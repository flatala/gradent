import { StateGraph, END, START, Annotation } from "@langchain/langgraph";
import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";
import { HumanMessage, AIMessage, BaseMessage } from "@langchain/core/messages";
import {
  ChatPromptTemplate,
  MessagesPlaceholder,
  SystemMessagePromptTemplate,
} from "@langchain/core/prompts";
import { ChatOpenAI } from "@langchain/openai";
import { WebPDFLoader } from "@langchain/community/document_loaders/web/pdf";
import { Runnable, RunnableConfig } from "@langchain/core/runnables";

// Add OpenRouter integration
const OPENROUTER_API_BASE = process.env.OPENROUTER_API_BASE;
const DEFAULT_MODEL_FALLBACK = "qwen/qwq-32b:free";

interface GenerateQuestionsParams {
  questionHeader: string;
  questionDescription: string;
  apiKey: string;
  uploadedFiles?: string[]; // Make optional
  fileUrls?: string[]; // Add fileUrls parameter
  siteUrl?: string; // For OpenRouter HTTP-Referer
  siteName?: string; // For OpenRouter X-Title
  modelName: string; // Changed from optional to required
  // stream option removed as streaming is now the default behavior
}

// Define state for our multi-agent system
const AgentState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (x, y) => x.concat(y),
  }),
  sender: Annotation<string>({
    reducer: (x, y) => y ?? x ?? "user",
    default: () => "user",
  }),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  extractedKeywords: Annotation<Record<string, any>>({
    reducer: (x, y) => ({ ...x, ...y }),
    default: () => ({}),
  }),
  questionContent: Annotation<string>({
    reducer: (_, y) => y,
    default: () => "",
  }),
  analysisResult: Annotation<string>({
    reducer: (_, y) => y,
    default: () => "",
  }),
  iterationCount: Annotation<number>({
    reducer: (x, y) => y ?? (x ?? 0) + 1,
    default: () => 0,
  }),
  isCompleted: Annotation<boolean>({
    reducer: (_, y) => y,
    default: () => false,
  }),
});

/**
 * Create a custom LLM client that uses OpenRouter instead of OpenAI directly
 */
class OpenRouterLLM extends ChatOpenAI {
  private siteUrl: string;
  private siteName: string;

  constructor(options: {
    openRouterApiKey: string;
    modelName?: string;
    temperature?: number;
    siteUrl?: string;
    siteName?: string;
  }) {
    super({
      modelName: options.modelName || DEFAULT_MODEL_FALLBACK,
      openAIApiKey: options.openRouterApiKey,
      temperature: options.temperature ?? 0.2,
      configuration: {
        baseURL: OPENROUTER_API_BASE,
      },
    });

    this.siteUrl = options.siteUrl || "http://localhost:3000";
    this.siteName = options.siteName || "QuestGen";
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async _generate(messages: any[], options?: any, runManager?: any) {
    // Add custom headers for OpenRouter
    const customHeaders = {
      "HTTP-Referer":
        process.env.NEXT_PUBLIC_OPENROUTER_SITE_URL || this.siteUrl,
      "X-Title": this.siteName,
    };

    // Merge headers with any existing ones
    if (!options) options = {};
    if (!options.headers) options.headers = {};
    options.headers = { ...options.headers, ...customHeaders };

    return super._generate(messages, options, runManager);
  }
}

/**
 * Create an agent from a prompt template
 */
async function createAgentWithPrompt(
  llm: ChatOpenAI,
  systemMessage: string
): Promise<Runnable> {
  const prompt = ChatPromptTemplate.fromMessages([
    SystemMessagePromptTemplate.fromTemplate(systemMessage),
    new MessagesPlaceholder("messages"),
  ]);

  return prompt.pipe(llm);
}

async function runAgentNode(props: {
  state: typeof AgentState.State;
  agent: Runnable;
  name: string;
  config?: RunnableConfig;
}) {
  const { state, agent, name, config } = props;

  // Log which agent is running
  console.log(`🤖 Agent Running: ${name}`);

  const result = await agent.invoke(state, config);

  // Convert the agent output to an AI message with the agent's name
  const aiMessage = new AIMessage({ content: result.content, name: name });

  // Log agent completion
  console.log(`✅ Agent Completed: ${name}`);

  return {
    messages: [aiMessage],
    sender: name,
  };
}

// Create a multi-agent workflow for question generation
export async function createMultiAgentWorkflow(
  apiKey: string,
  options?: {
    siteUrl?: string;
    siteName?: string;
    modelName?: string;
  }
) {
  // Create LLM using OpenRouter
  const llm = new OpenRouterLLM({
    openRouterApiKey: apiKey,
    modelName: options?.modelName || DEFAULT_MODEL_FALLBACK,
    temperature: 0.6,
    siteUrl: options?.siteUrl,
    siteName: options?.siteName,
  });

  // Create agents with appropriate system prompts
  const extractorAgent = await createAgentWithPrompt(
    llm,
    `You are the Extractor Agent. Your job is to analyze the input text and extract key information about the requested question paper.
     Extract the following information:
     1. Exam Type (mid-term, quiz, final, etc.)
     2. Total Marks
     3. Question Difficulty Levels (easy, hard, conceptual, etc.)
     4. Question Types (MCQ, true-false, short theory, long theory)
     5. Subject Areas or Topics

     Format your response as a structured JSON object with these keys. Be specific and detailed in your extraction.
     DO NOT make up information that isn't in the input text. If information is missing, use reasonable defaults based on the available context.`
  );

  const questionCreatorAgent = await createAgentWithPrompt(
    llm,
    `You are the Question Creator Agent. Your job is to create high-quality questions based on the specified question types.
     Create questions that are clear, specific, and relevant to the content provided.
     For MCQs: Include 4 options with one correct answer.
     For True/False: Create unambiguous statements.
     For Short Theory: Create questions that require brief explanations (1-3 paragraphs).
     For Long Theory: Create questions that require in-depth analysis and explanation.

     Match the difficulty level specified in the requirements. If multiple question types are requested, create a balanced mix.
     Base all questions ONLY on the content provided to ensure they are answerable from the material.
     Include the correct answers where applicable.`
  );

  // QuestionAnalysis and Decider agents removed for simplified workflow
  // Workflow now goes: Extractor → QuestionCreator → Formatter

  const formatterAgent = await createAgentWithPrompt(
    llm,
    `You are the Question Formatter Agent. Your job is to format the finalized questions into a professional, well-organized exam paper.

     Format the exam paper with:
     1. A clear title and header with exam details
     2. Organized sections by question type
     3. Clear numbering and marks allocation
     4. Professional layout and spacing
     5. Instructions for each section

     Ensure consistency in formatting throughout the document.
     Present the questions in a logical order, typically from easier to more difficult.
     If answers are to be included, must format them in a separate section at the end.

     Your output should be a complete, ready-to-use exam paper.`
  );

  // Define agent nodes
  async function extractorNode(
    state: typeof AgentState.State,
    config?: RunnableConfig
  ) {
    console.log("🔍 Starting Extractor Agent...");
    // Only provide question header and description, not the PDF content
    const messages = [...state.messages];
    const userMessage = messages.find(
      (msg) => msg instanceof HumanMessage
    ) as HumanMessage;

    if (userMessage) {
      const content = userMessage.content as string;
      // Extract just the header and description part, not the PDF content
      const headerDescriptionPart = content.split(
        "Content to generate questions from:"
      )[0];

      // Replace the original message with just header and description
      const newMessage = new HumanMessage({
        content: `Extract key information from this request: ${headerDescriptionPart}`,
      });

      const extractorState = {
        ...state,
        messages: [newMessage],
      };

      return runAgentNode({
        state: extractorState,
        agent: extractorAgent,
        name: "Extractor",
        config,
      });
    }

    return runAgentNode({
      state,
      agent: extractorAgent,
      name: "Extractor",
      config,
    });
  }

  async function questionCreatorNode(
    state: typeof AgentState.State,
    config?: RunnableConfig
  ) {
    console.log("📝 Starting Question Creator Agent...");
    // Include extracted keywords, original prompt with PDF content
    const messages = [...state.messages];
    const extractorMessage = messages.find((msg) => msg.name === "Extractor");
    const originalMessage = messages.find(
      (msg) => msg instanceof HumanMessage
    ) as HumanMessage;

    if (extractorMessage && originalMessage) {
      const extractorContent = extractorMessage.content as string;
      console.log(
        "📋 Using extracted information:",
        extractorContent.substring(0, 100) + "..."
      );

      // Add a human message with instructions that includes PDF content and extractor keywords
      messages.push(
        new HumanMessage({
          content: `Create questions based on these requirements:
1. Use the extracted keywords and requirements: ${extractorContent}
2. Original request: ${originalMessage.content}
Create appropriate questions using the provided PDF content.`,
        })
      );
    }

    const updatedState = { ...state, messages };

    const result = await runAgentNode({
      state: updatedState,
      agent: questionCreatorAgent,
      name: "QuestionCreator",
      config,
    });

    // Store the created questions
    return {
      ...result,
      questionContent: result.messages[0].content,
    };
  }

  // QuestionAnalysisNode and DeciderNode removed - workflow goes directly to formatter

  async function formatterNode(
    state: typeof AgentState.State,
    config?: RunnableConfig
  ) {
    console.log("📄 Starting Formatter Agent...");
    // Format the questions created by QuestionCreator
    const messages = [...state.messages];
    const creatorMessage = messages.find(
      (msg) => msg.name === "QuestionCreator"
    );

    if (creatorMessage) {
      console.log("📋 Formatting final exam paper");
      messages.push(
        new HumanMessage({
          content: `Format these questions into a professional exam paper:
${creatorMessage.content}

Create a well-structured, professional exam paper.`,
        })
      );
    }

    const updatedState = { ...state, messages };

    const result = await runAgentNode({
      state: updatedState,
      agent: formatterAgent,
      name: "Formatter",
      config,
    });

    // Mark as completed
    console.log("🎉 Question generation process completed!");
    return {
      ...result,
      isCompleted: true,
    };
  }

  // Router function to determine the next step
  function mainRouter(state: typeof AgentState.State) {
    const messages = state.messages;
    const lastMessage = messages[messages.length - 1] as AIMessage;

    if (lastMessage.name === "Extractor") {
      console.log("🔄 Router: Extractor → Question Creator");
      return "to_question_creator";
    } else if (lastMessage.name === "QuestionCreator") {
      console.log("🔄 Router: Question Creator → Formatter");
      return "to_formatter";
    } else if (lastMessage.name === "Formatter") {
      console.log("🔄 Router: Formatter → End");
      return "end";
    }

    console.log("🔄 Router: Continue with current agent");
    return "continue";
  }

  // Create the graph
  const workflow = new StateGraph(AgentState)
    // Add nodes (QuestionAnalysis and Decider removed)
    .addNode("Extractor", extractorNode)
    .addNode("QuestionCreator", questionCreatorNode)
    .addNode("Formatter", formatterNode);

  // Add edges for the simplified workflow
  workflow.addConditionalEdges("Extractor", mainRouter, {
    to_question_creator: "QuestionCreator",
    continue: "Extractor",
  });

  workflow.addConditionalEdges("QuestionCreator", mainRouter, {
    to_formatter: "Formatter",
    continue: "QuestionCreator",
  });

  // Simplify the Formatter edge to always end the workflow
  // No conditional routing needed - always terminate after Formatter
  workflow.addEdge("Formatter", END);

  // Starting point
  workflow.addEdge(START, "Extractor");

  return workflow.compile();
}

// Optimized to handle concurrent agent execution issues with streaming by default
export async function generateQuestions({
  questionHeader,
  questionDescription,
  apiKey,
  fileUrls = [],
  siteUrl,
  siteName,
  modelName,
}: GenerateQuestionsParams) {
  console.log("🚀 Starting question generation process with streaming enabled");

  // New function to process PDF URLs
  const processPDFUrls = async (urls: string[]) => {
    try {
      const allDocs = [];

      for (const url of urls) {
        try {
          console.log(`Processing PDF URL: ${url}`);

          try {
            // Fetch the PDF directly using fetch API first
            console.log(`Fetching PDF from URL: ${url}`);
            const response = await fetch(url);

            if (!response.ok) {
              throw new Error(
                `Failed to fetch PDF: ${response.status} ${response.statusText}`
              );
            }

            // Get the array buffer from the response
            const arrayBuffer = await response.arrayBuffer();
            console.log(`Received PDF data: ${arrayBuffer.byteLength} bytes`);

            // Convert to Uint8Array which WebPDFLoader can handle from memory
            const uint8Array = new Uint8Array(arrayBuffer);

            // Use WebPDFLoader with the blob data directly
            const loader = new WebPDFLoader(
              new Blob([uint8Array], { type: "application/pdf" })
            );

            console.log("Loading PDF content with WebPDFLoader...");
            const docs = await loader.load();
            console.log(`Loaded ${docs.length} documents from PDF`);

            allDocs.push(...docs);
            console.log(`Successfully processed PDF from URL: ${url}`);
          } catch (loadError) {
            console.error(`Error processing PDF from URL ${url}:`, loadError);
          }
        } catch (urlError) {
          console.error(`Error processing URL ${url}:`, urlError);
        }
      }

      // Split documents into chunks
      const textSplitter = new RecursiveCharacterTextSplitter({
        chunkSize: 4000,
        chunkOverlap: 200,
      });

      console.log(`Splitting ${allDocs.length} documents from URLs`);
      const splitDocs = await textSplitter.splitDocuments(allDocs);
      console.log(`Split into ${splitDocs.length} chunks`);
      return splitDocs;
    } catch (error) {
      console.error("Error processing PDF URLs:", error);
      throw new Error(
        `Failed to process PDF URLs: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    }
  };

  try {
    // Process files from either local paths or URLs based on what's available
    console.log("📚 Processing PDF files");

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let fileDocs: any[] = [];

    // If we have URLs, process those
    if (fileUrls && fileUrls.length > 0) {
      console.log(`Processing ${fileUrls.length} PDF URLs`);
      fileDocs = await processPDFUrls(fileUrls);
    }

    const fileText = fileDocs.map((doc) => doc.pageContent).join("\n\n");
    console.log(`📄 Extracted ${fileText.length} characters of text from PDFs`);

    // Combine file text with question header and description
    const inputPrompt = `
Question Header: ${questionHeader}
Question Description: ${questionDescription}

Content to generate questions from:
${fileText}
    `;

    // Create and execute the workflow with OpenRouter options
    console.log("🔄 Creating multi-agent workflow");
    const workflow = await createMultiAgentWorkflow(apiKey, {
      siteUrl,
      siteName,
      modelName,
    });

    console.log("🚀 Invoking multi-agent workflow with streaming");

    // Add an initial state with iteration count 0
    const initialState = {
      messages: [new HumanMessage(inputPrompt)],
      iterationCount: 0,
    };
    const config = {
      configurable: {
        thread_id: "stream_events",
      },
    };

    // Always stream results
    console.log("📊 Streaming mode enabled");

    // Return the stream directly so it can be consumed by the API route
    return {
      success: true,
      stream: await workflow.stream(initialState, config),

      streamEvents: true, // Flag to indicate we're returning a stream
    };
  } catch (error) {
    console.error("❌ Generation Error:", error);
    return {
      success: false,
      error: `Failed to generate questions: ${
        error instanceof Error ? error.message : String(error)
      }`,
      streamEvents: false,
    };
  }
}
