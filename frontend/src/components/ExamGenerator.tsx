import { useState, useEffect, type ChangeEvent, type DragEvent, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Upload,
  X,
  FileText,
  Sparkles,
  Download,
  Copy,
  CheckCircle,
  ArrowLeft,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";
import { api } from "@/lib/api";

interface ExamGeneratorProps {
  assignmentContext?: {
    title: string;
    course: string;
    topics: string[];
    description?: string;
  };
  onBack?: () => void;
}

type ExamType = "multiple-choice" | "open-questions" | "custom";

const ExamGenerator = ({ assignmentContext, onBack }: ExamGeneratorProps) => {
  const [files, setFiles] = useState<File[]>([]);
  const [questionHeader, setQuestionHeader] = useState("AI Generated Exam");
  const [examType, setExamType] = useState<ExamType>("multiple-choice");
  const [customDescription, setCustomDescription] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [modelName, setModelName] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [processedFiles, setProcessedFiles] = useState<string[]>([]);

  // Generate question description based on exam type and assignment context
  const getQuestionDescription = (): string => {
    let baseDescription = "";
    
    if (assignmentContext) {
      const topicsText = assignmentContext.topics.length > 0
        ? ` Focus on: ${assignmentContext.topics.join(", ")}.`
        : "";
      baseDescription = `Generate exam questions for ${assignmentContext.course} - ${assignmentContext.title}.${topicsText}`;
    }

    switch (examType) {
      case "multiple-choice":
        return `${baseDescription} Create 10 multiple-choice questions with 4 options each. Mark the correct answer clearly.`;
      case "open-questions":
        return `${baseDescription} Create 5 open-ended questions that require detailed written responses.`;
      case "custom":
        return customDescription || baseDescription;
      default:
        return baseDescription;
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    const pdfFiles = selectedFiles.filter(
      (file) => file.type === "application/pdf",
    );

    if (pdfFiles.length !== selectedFiles.length) {
      alert("Only PDF files are allowed");
    }

    setFiles((prev) => [...prev, ...pdfFiles]);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    const pdfFiles = droppedFiles.filter(
      (file) => file.type === "application/pdf",
    );

    if (pdfFiles.length !== droppedFiles.length) {
      alert("Only PDF files are allowed");
    }

    setFiles((prev) => [...prev, ...pdfFiles]);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (files.length === 0) {
      alert("Please upload at least one PDF file");
      return;
    }

    const finalDescription = getQuestionDescription();
    if (!finalDescription.trim()) {
      alert("Please select an exam type or provide custom requirements");
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);
    setProgress(0);
    setProcessedFiles([]);

    // Simulate progress
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 10;
      });
    }, 500);

    try {
      const data = await api.generateExam({
        files,
        questionHeader,
        questionDescription: finalDescription,
        apiKey,
        modelName,
      });

      if (data.success && data.questions) {
        setResults(data.questions);
        setProcessedFiles(
          data.uploaded_files && data.uploaded_files.length > 0
            ? data.uploaded_files
            : files.map((file) => file.name),
        );
        setProgress(100);
      } else {
        setError(data.error || "No questions were generated. Please adjust your input.");
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      clearInterval(progressInterval);
      setLoading(false);
      setTimeout(() => setProgress(0), 1000);
    }
  };

  const handleReset = () => {
    setResults(null);
    setError(null);
    setFiles([]);
    setProcessedFiles([]);
    setExamType("multiple-choice");
    setCustomDescription("");
    setQuestionHeader("AI Generated Exam");
    setApiKey("");
    setModelName("");
  };

  const handleCopy = () => {
    if (results) {
      navigator.clipboard.writeText(results);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (results) {
      const blob = new Blob([results], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "exam.md";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  if (results) {
    return (
      <div className="space-y-6 animate-fade-in">
        {onBack && (
          <Button
            variant="ghost"
            onClick={onBack}
            className="mb-4"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
        )}
        <Card className="shadow-lg bg-gradient-card">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl flex items-center gap-2">
                  <CheckCircle className="w-6 h-6 text-success" />
                  Exam Generated Successfully!
                </CardTitle>
                <CardDescription>
                  Your AI-generated exam is ready
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleReset} variant="outline">
                  Generate Another
                </Button>
                {onBack && (
                  <Button onClick={onBack} variant="secondary">
                    Exit Exam
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {processedFiles.length > 0 && (
              <div className="mb-6">
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  Processed Files
                </p>
                <ul className="list-disc list-inside text-sm space-y-1 text-muted-foreground">
                  {processedFiles.map((file) => (
                    <li key={file}>{file}</li>
                  ))}
                </ul>
              </div>
            )}

            <Tabs defaultValue="preview" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-4">
                <TabsTrigger value="preview">Preview</TabsTrigger>
                <TabsTrigger value="markdown">Markdown</TabsTrigger>
              </TabsList>

              <TabsContent value="preview" className="space-y-4">
                <div className="prose prose-slate max-w-none markdown-content bg-card p-6 rounded-lg border">
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {results}
                  </ReactMarkdown>
                </div>
              </TabsContent>

              <TabsContent value="markdown" className="space-y-4">
                <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                  <code>{results}</code>
                </pre>
              </TabsContent>
            </Tabs>

            <Separator className="my-6" />

            <div className="flex gap-3">
              <Button
                onClick={handleDownload}
                className="flex-1 bg-gradient-primary shadow-md hover:shadow-glow"
              >
                <Download className="w-4 h-4 mr-2" />
                Download Markdown
              </Button>
              <Button onClick={handleCopy} variant="outline" className="flex-1">
                {copied ? (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2 text-success" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-2" />
                    Copy to Clipboard
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {onBack && (
        <Button
          variant="ghost"
          onClick={onBack}
          className="mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>
      )}
      {!loading && (
        <Card className="shadow-lg hover:shadow-glow transition-all duration-300 bg-gradient-card border-border/50 animate-fade-in">
          <CardHeader className="pb-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-gradient-primary rounded-lg flex items-center justify-center shadow-md">
                <Upload className="w-5 h-5 text-white" />
              </div>
              <CardTitle className="text-3xl">Create Your Exam</CardTitle>
            </div>
            <CardDescription className="text-base">
              Upload your study materials and let AI generate tailored exam
              questions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Upload Area */}
              <div className="space-y-2">
                <Label htmlFor="files">
                  Upload PDF Files <span className="text-destructive">*</span>
                </Label>
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200 ${
                    dragOver
                      ? "border-primary bg-primary/5"
                      : "border-muted-foreground/25 hover:border-primary/50 hover:bg-accent/50"
                  }`}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onClick={() => document.getElementById("file-input")?.click()}
                >
                  <input
                    id="file-input"
                    type="file"
                    multiple
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-lg font-medium mb-1">
                    Click to upload or drag and drop
                  </p>
                  <p className="text-sm text-muted-foreground">
                    PDF files only (max 10 files)
                  </p>
                </div>

                {/* File List */}
                {files.length > 0 && (
                  <div className="mt-4 space-y-2">
                    {files.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-3 bg-accent rounded-lg"
                      >
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-primary" />
                          <span className="text-sm font-medium">
                            {file.name}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            ({(file.size / 1024).toFixed(1)} KB)
                          </span>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeFile(index)}
                          className="h-8 w-8 p-0"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Question Requirements */}
              <div className="space-y-2">
                <Label htmlFor="questionHeader">
                  Exam Title <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="questionHeader"
                  placeholder="e.g., Midterm Exam - Linear Algebra"
                  value={questionHeader}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setQuestionHeader(e.target.value)}
                  required
                  className="text-base"
                />
              </div>

              <div className="space-y-3">
                <Label>
                  Exam Type <span className="text-destructive">*</span>
                </Label>
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <input
                      type="radio"
                      id="multiple-choice"
                      name="examType"
                      value="multiple-choice"
                      checked={examType === "multiple-choice"}
                      onChange={(e) => setExamType(e.target.value as ExamType)}
                      className="w-4 h-4 text-primary"
                    />
                    <Label htmlFor="multiple-choice" className="font-normal cursor-pointer">
                      10 Multiple Choice Questions
                    </Label>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <input
                      type="radio"
                      id="open-questions"
                      name="examType"
                      value="open-questions"
                      checked={examType === "open-questions"}
                      onChange={(e) => setExamType(e.target.value as ExamType)}
                      className="w-4 h-4 text-primary"
                    />
                    <Label htmlFor="open-questions" className="font-normal cursor-pointer">
                      5 Open-Ended Questions
                    </Label>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <input
                      type="radio"
                      id="custom"
                      name="examType"
                      value="custom"
                      checked={examType === "custom"}
                      onChange={(e) => setExamType(e.target.value as ExamType)}
                      className="w-4 h-4 text-primary"
                    />
                    <Label htmlFor="custom" className="font-normal cursor-pointer">
                      Custom
                    </Label>
                  </div>
                  
                  {examType === "custom" && (
                    <Textarea
                      id="customDescription"
                      placeholder="e.g., Generate 15 questions: 10 MCQ and 5 short answer, covering advanced topics"
                      value={customDescription}
                      onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setCustomDescription(e.target.value)}
                      className="min-h-[100px] text-base mt-2"
                    />
                  )}
                </div>
                <p className="text-xs text-muted-foreground">
                  {examType === "custom" 
                    ? "Specify your custom exam requirements"
                    : "The questions will be based on the uploaded materials and assignment topics"}
                </p>
              </div>

              {/* Optional Settings */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="apiKey">OpenRouter API Key (optional)</Label>
                  <Input
                    id="apiKey"
                    type="password"
                    placeholder="Overrides server API key"
                    value={apiKey}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setApiKey(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Leave blank to use the backend configuration.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="modelName">Model Name (optional)</Label>
                  <Input
                    id="modelName"
                    placeholder="e.g., meta-llama/llama-4-scout:free"
                    value={modelName}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setModelName(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Defaults to the server-configured model.
                  </p>
                </div>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full h-12 text-base font-semibold bg-gradient-primary hover:opacity-90 transition-opacity shadow-md hover:shadow-glow"
                size="lg"
              >
                <Sparkles className="w-5 h-5 mr-2" />
                Generate Exam
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {loading && (
        <Card className="shadow-lg animate-fade-in">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 animate-spin text-primary" />
              Generating Your Exam
            </CardTitle>
            <CardDescription>
              Our AI is analyzing your PDFs and crafting tailored questions...
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Progress value={progress} className="w-full h-3" />
            <p className="text-sm text-muted-foreground text-center">
              This may take 30-60 seconds. Please wait...
            </p>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card className="border-destructive shadow-lg animate-fade-in">
          <CardContent className="pt-6">
            <Alert variant="destructive" className="mb-4">
              <AlertDescription className="flex items-center gap-2">
                <span className="font-semibold">Error:</span> {error}
              </AlertDescription>
            </Alert>
            <Button
              onClick={handleReset}
              className="w-full bg-gradient-primary hover:opacity-90 shadow-md"
            >
              Try Again
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ExamGenerator;
