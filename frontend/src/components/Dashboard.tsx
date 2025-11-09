import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Calendar,
  BookOpen,
  Brain,
  TrendingUp,
  CheckCircle2,
  CheckCircle,
  Loader2,
  RefreshCw,
  Sparkles,
  X,
  Eye,
  EyeOff,
} from "lucide-react";
import AssignmentCard, { type ExamType } from "./AssignmentCard";
import ResultsView from "./ResultsView";
import ScheduleAdjustment from "./ScheduleAdjustment";
import { CalendarSync } from "./CalendarSync";
import { api } from "@/lib/api";
import type { SuggestionRecord } from "@/lib/types";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

const CONSENT_STORAGE_KEY = "gradent_services_consent";

const Dashboard = () => {
  const { toast } = useToast();
  const [showConsent, setShowConsent] = useState(false);

  // Initialize isConnected from localStorage
  const [isConnected, setIsConnected] = useState(() => {
    try {
      const stored = localStorage.getItem(CONSENT_STORAGE_KEY);
      return stored === "true";
    } catch {
      return false;
    }
  });

  const [currentView, setCurrentView] = useState<
    "dashboard" | "results" | "schedule" | "calendar"
  >("dashboard");
  const [syncStatus, setSyncStatus] = useState<"idle" | "syncing" | "synced">(
    "idle",
  );
  const [selectedAssignment, setSelectedAssignment] = useState<any>(null);
  const [examResults, setExamResults] = useState<any>(null);
  const [examGeneratingFor, setExamGeneratingFor] = useState<string | null>(null);
  const [generatedExams, setGeneratedExams] = useState<Record<string, string>>({});
  const [viewingExamFor, setViewingExamFor] = useState<string | null>(null);
  const [showAnswers, setShowAnswers] = useState(false);
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({});
  const [assessmentResult, setAssessmentResult] = useState<any>(null);
  const [isAssessing, setIsAssessing] = useState(false);
  const [assignments, setAssignments] = useState<any[]>([]);
  const [assignmentsLoading, setAssignmentsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<SuggestionRecord[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);

  // Fetch assignments from API
  useEffect(() => {
    const fetchAssignments = async () => {
      setAssignmentsLoading(true);
      try {
        const response = await api.getAssignments();
        setAssignments(response.assignments);
      } catch (error) {
        console.error("Failed to fetch assignments:", error);
        toast({
          title: "Error",
          description: "Failed to load assignments",
          variant: "destructive",
        });
      } finally {
        setAssignmentsLoading(false);
      }
    };

    fetchAssignments();
  }, []);

  const handleConnect = () => {
    setShowConsent(true);
  };

  const handleConsent = () => {
    setShowConsent(false);
    setIsConnected(true);
    setSyncStatus("syncing");

    // Cache consent in localStorage so modal doesn't show again
    try {
      localStorage.setItem(CONSENT_STORAGE_KEY, "true");
    } catch (error) {
      console.error("Failed to save consent to localStorage:", error);
    }

    setTimeout(() => {
      setSyncStatus("synced");
    }, 3000);
  };

  const handleStartExam = async (
    assignment: any,
    examType: ExamType,
    customInstructions?: string
  ) => {
    setSelectedAssignment(assignment);
    setExamGeneratingFor(assignment.id);

    try {
      // Build question description based on exam type
      let questionDescription = "";
      const topicsText = assignment.topics?.length > 0
        ? ` Focus on: ${assignment.topics.join(", ")}.`
        : "";
      
      const baseDescription = `for ${assignment.courseName || assignment.course} - ${assignment.title}.${topicsText}`;
      
      if (examType === "multiple-choice") {
        questionDescription = `Generate 10 multiple choice questions with 4 options each ${baseDescription} IMPORTANT: Do NOT include the correct answer next to each question. Place all answers in a separate section at the end of the exam.`;
      } else if (examType === "open-questions") {
        questionDescription = `Generate 5 open-ended questions that require detailed written responses ${baseDescription} IMPORTANT: Do NOT include sample answers or solutions next to the questions. Place all answers in a separate section at the end.`;
      } else if (examType === "custom" && customInstructions) {
        questionDescription = `${customInstructions} ${baseDescription} IMPORTANT: Do NOT include answers next to the questions. Place all answers in a separate section at the end.`;
      }

      // Add assignment description if available
      if (assignment.description) {
        questionDescription += ` Context: ${assignment.description}`;
      }

      toast({
        title: "Generating exam...",
        description: `Creating ${examType === "multiple-choice" ? "10 multiple choice" : examType === "open-questions" ? "5 open" : "custom"} questions for ${assignment.title}`,
      });

      // Call the API with default PDFs (no file upload needed)
      const data = await api.generateExam({
        questionHeader: `${assignment.title} - Mock Exam`,
        questionDescription,
        useDefaultPdfs: true,
      });

      if (data.success && data.questions) {
        setGeneratedExams(prev => ({
          ...prev,
          [assignment.id]: data.questions!
        }));
        toast({
          title: "Exam generated!",
          description: `Your mock exam for ${assignment.title} is ready.`,
        });
      } else {
        throw new Error(data.error || "Failed to generate exam");
      }
    } catch (error: any) {
      const errorMessage = error.message || "Failed to generate exam";
      const isRateLimit = errorMessage.includes("rate-limited") || 
                          errorMessage.includes("busy") || 
                          errorMessage.includes("Rate limit");
      
      toast({
        title: isRateLimit ? "Service Busy" : "Generation failed",
        description: errorMessage,
        variant: "destructive",
        duration: isRateLimit ? 8000 : 5000, // Show longer for rate limit errors
      });
    } finally {
      setExamGeneratingFor(null);
    }
  };

  const handleViewExam = (assignment: any) => {
    setViewingExamFor(assignment.id);
    setSelectedAssignment(assignment);
    setShowAnswers(false); // Reset answer visibility when viewing new exam
    setUserAnswers({});
    setAssessmentResult(null);
  };

  const handleExitExam = () => {
    setViewingExamFor(null);
    setSelectedAssignment(null);
    setShowAnswers(false);
    setUserAnswers({});
    setAssessmentResult(null);
  };

  const handleAssessExam = async () => {
    if (!viewingExamFor || !selectedAssignment) return;
    
    const examContent = generatedExams[viewingExamFor];
    if (!examContent) return;

    // Parse the exam to get questions
    const questions = parseExam(examContent);
    if (questions.length === 0) {
      toast({
        title: "Error",
        description: "Unable to parse exam questions",
        variant: "destructive",
      });
      return;
    }

    // Extract correct answers from exam content
    const correctAnswers: Record<string, string> = {};
    const answerSection = examContent.split(/\*\*(?:Section B:|Answers)\*\*/i)[1];
    if (answerSection) {
      const answerLines = answerSection.split('\n');
      for (const line of answerLines) {
        const match = line.match(/^\*?\*?(\d+)\.\s*([A-D])\)?/i);
        if (match) {
          correctAnswers[match[1]] = match[2].toUpperCase();
        }
      }
    }

    setIsAssessing(true);

    try {
      const payload = {
        assignment_title: selectedAssignment.title,
        course_name: selectedAssignment.courseName || selectedAssignment.course,
        questions: questions.map(q => ({
          number: q.number.toString(),
          text: q.text,
          options: q.options || [],
        })),
        user_answers: userAnswers,
        correct_answers: correctAnswers,
      };

      console.log('Sending assessment payload:', payload);

      const result = await api.assessExam({
        assignmentTitle: selectedAssignment.title,
        courseName: selectedAssignment.courseName || selectedAssignment.course,
        questions: questions.map(q => ({
          number: q.number.toString(),
          text: q.text,
          options: q.options || [],
        })),
        userAnswers: userAnswers,
        correctAnswers: correctAnswers,
      });

      if (result.success) {
        setAssessmentResult(result);
        toast({
          title: "Exam Assessed!",
          description: `Score: ${result.score}/${result.total_questions} (${result.percentage}%)`,
        });
      } else {
        toast({
          title: "Assessment failed",
          description: result.error || "Unknown error",
          variant: "destructive",
        });
      }
    } catch (error: any) {
      toast({
        title: "Assessment failed",
        description: error.message || "Failed to assess exam",
        variant: "destructive",
      });
    } finally {
      setIsAssessing(false);
    }
  };

  // Parse exam content into structured questions (handles both multiple choice and open-ended)
  const parseExam = (examContent: string) => {
    const questions: any[] = [];
    
    if (!examContent) {
      console.log('No exam content to parse');
      return questions;
    }
    
    console.log('=== PARSING EXAM ===');
    console.log('Content length:', examContent.length);
    
    const lines = examContent.split('\n');
    let currentQuestion: any = null;
    let currentOptions: string[] = [];
    let insideQuestions = false;
    let questionText: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      // Detect when we're in the questions section
      if (line.includes('Section A:') || line.includes('Section B:') || 
          line.includes('Multiple Choice Questions') || line.includes('**Section A:') ||
          line.includes('Open-Ended Questions') || line.includes('Collaborative Filtering')) {
        insideQuestions = true;
        console.log('Found questions section at line', i, ':', line);
        continue;
      }
      
      // Stop parsing at "Answers" section (but not "Section B" as it might contain more questions)
      if (line === 'Answers' || line === '**Answers**' || line.match(/^#{1,3}\s*Answers?$/i) ||
          line === '## Answers' || line.includes('(Answers will be provided')) {
        console.log('Found Answers section at line', i);
        break;
      }
      
      // Skip empty lines, instructions, and notes
      if (!line || line.includes('Instructions:') || line.includes('Choose the correct') || 
          line.includes('This exam consists') || line.includes('Answer all questions') ||
          line.includes('Make sure to provide') || line.includes('The total exam duration') ||
          line.startsWith('*') && !line.startsWith('**')) {
        continue;
      }
      
      // Match question pattern: "### Question 1" or "**1. What is...**" or "1. What is..."
      const questionHeaderMatch = line.match(/^###\s*Question\s+(\d+)/i);
      const questionInlineMatch = line.match(/^\*\*(\d+)\.\s+(.+?)\*\*$/) || line.match(/^(\d+)\.\s+(.+)$/);
      
      if (questionHeaderMatch) {
        // Save previous question
        if (currentQuestion) {
          if (questionText.length > 0) {
            currentQuestion.text = questionText.join(' ').trim();
          }
          if (currentOptions.length > 0) {
            currentQuestion.options = currentOptions;
          }
          questions.push(currentQuestion);
          console.log(`Added question ${currentQuestion.number}, type: ${currentQuestion.type}`);
        }
        
        // Start new question (open-ended style with header)
        currentQuestion = {
          number: questionHeaderMatch[1],
          text: '',
          type: 'open-ended'
        };
        questionText = [];
        currentOptions = [];
        console.log(`Found open-ended question ${questionHeaderMatch[1]}`);
        continue;
      }
      
      if (questionInlineMatch && insideQuestions) {
        // Save previous question
        if (currentQuestion) {
          if (questionText.length > 0) {
            currentQuestion.text = questionText.join(' ').trim();
          }
          if (currentOptions.length > 0) {
            currentQuestion.options = currentOptions;
          }
          questions.push(currentQuestion);
          console.log(`Added question ${currentQuestion.number}, type: ${currentQuestion.type}`);
        }
        
        // Start new question (inline style, likely multiple choice)
        currentQuestion = {
          number: questionInlineMatch[1],
          text: questionInlineMatch[2].replace(/\*\*/g, '').trim(),
          type: 'multiple-choice'
        };
        questionText = [];
        currentOptions = [];
        console.log(`Found inline question ${questionInlineMatch[1]}: ${currentQuestion.text.substring(0, 50)}...`);
        continue;
      }
      
      // Match options: A) text or **A)** text
      const optionMatch = line.match(/^([A-D])\)\s+(.+)$/);
      if (optionMatch && currentQuestion) {
        currentOptions.push(optionMatch[2]);
        currentQuestion.type = 'multiple-choice'; // Confirm it's multiple choice
        console.log(`  Found option ${optionMatch[1]}: ${optionMatch[2].substring(0, 40)}...`);
        continue;
      }
      
      // If we have a current question and this is regular text, it's part of the question
      if (currentQuestion && !questionInlineMatch && !questionHeaderMatch && !optionMatch) {
        questionText.push(line);
      }
    }
    
    // Don't forget the last question
    if (currentQuestion) {
      if (questionText.length > 0) {
        currentQuestion.text = questionText.join(' ').trim();
      }
      if (currentOptions.length > 0) {
        currentQuestion.options = currentOptions;
      }
      questions.push(currentQuestion);
      console.log(`Added final question ${currentQuestion.number}, type: ${currentQuestion.type}`);
    }
    
    console.log('=== PARSING COMPLETE ===');
    console.log('Total questions found:', questions.length);
    
    return questions;
  };

  const handleExamComplete = (results: any) => {
    setExamResults(results);
    setCurrentView("results");
  };

  const handleViewSchedule = () => {
    setCurrentView("schedule");
  };

  const handleBackToDashboard = () => {
    setCurrentView("dashboard");
  };

  const fetchSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);
    setSuggestionsError(null);
    try {
      const response = await api.listSuggestions();
      setSuggestions(response.suggestions);
    } catch (err) {
      setSuggestionsError((err as Error).message);
    } finally {
      setSuggestionsLoading(false);
    }
  }, []);

  const handleGenerateSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);
    setSuggestionsError(null);
    try {
      const response = await api.generateSuggestions();
      setSuggestions(response.suggestions);
    } catch (err) {
      setSuggestionsError((err as Error).message);
    } finally {
      setSuggestionsLoading(false);
    }
  }, []);

  const handleResetSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);
    setSuggestionsError(null);
    try {
      await api.resetSuggestions({});
      const response = await api.listSuggestions();
      setSuggestions(response.suggestions);
    } catch (err) {
      setSuggestionsError((err as Error).message);
    } finally {
      setSuggestionsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (syncStatus === "synced") {
      fetchSuggestions();
    }
  }, [syncStatus, fetchSuggestions]);

  const renderMainContent = () => {
    if (currentView === "results") {
      return (
        <ResultsView
          results={examResults}
          onViewSchedule={handleViewSchedule}
          onBack={handleBackToDashboard}
        />
      );
    }

    if (currentView === "schedule") {
      return (
        <ScheduleAdjustment
          results={examResults}
          onBack={handleBackToDashboard}
        />
      );
    }

    if (currentView === "calendar") {
      return <CalendarSync />;
    }

    return (
      <div className="space-y-8">
        <div className="space-y-6 animate-fade-in">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">Upcoming Assignments</h2>
            <Button
              variant="outline"
              onClick={() => setCurrentView("calendar")}
              className="gap-2"
            >
              <Calendar className="h-4 w-4" />
              View Calendar
            </Button>
          </div>
            {assignmentsLoading ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <Card key={i} className="p-6">
                    <Skeleton className="h-6 w-3/4 mb-4" />
                    <Skeleton className="h-4 w-1/2 mb-4" />
                    <Skeleton className="h-4 w-full mb-2" />
                    <Skeleton className="h-4 w-2/3" />
                  </Card>
                ))}
              </div>
            ) : assignments.length === 0 ? (
              <Card className="p-8 text-center">
                <p className="text-muted-foreground">
                  No assignments found. Please sync your Brightspace account.
                </p>
              </Card>
            ) : viewingExamFor ? (
              <div className="space-y-4">
                <Card className="p-8 bg-card border-border max-w-5xl mx-auto">
                  <div className="mb-6 pb-4 border-b border-border">
                    <h2 className="text-2xl font-bold text-foreground">{selectedAssignment?.title}</h2>
                    <p className="text-sm text-muted-foreground mt-1">{selectedAssignment?.courseName}</p>
                  </div>
                  
                  {/* Interactive exam display */}
                  <div className="space-y-6">
                    {parseExam(generatedExams[viewingExamFor] || "").map((question) => (
                      <div key={question.number} className="space-y-3 p-4 rounded-lg bg-muted/30">
                        <div className="flex gap-3">
                          <span className="font-bold text-primary text-lg flex-shrink-0">{question.number}.</span>
                          <p className="text-foreground leading-relaxed">{question.text}</p>
                        </div>
                        
                        {/* Multiple choice options */}
                        {question.type === 'multiple-choice' && question.options && (
                          <div className="ml-8 space-y-2">
                            {question.options.map((option: string, idx: number) => {
                              const optionLetter = String.fromCharCode(65 + idx); // A, B, C, D
                              const isSelected = userAnswers[question.number] === optionLetter;
                              
                              return (
                                <button
                                  key={idx}
                                  onClick={() => {
                                    setUserAnswers(prev => ({
                                      ...prev,
                                      [question.number]: optionLetter
                                    }));
                                  }}
                                  className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
                                    isSelected
                                      ? 'border-primary bg-primary/10'
                                      : 'border-border bg-background hover:border-primary/50 hover:bg-muted'
                                  } cursor-pointer`}
                                >
                                  <div className="flex items-start gap-3">
                                    <span className={`font-semibold flex-shrink-0 ${
                                      isSelected ? 'text-primary' : 'text-foreground'
                                    }`}>
                                      {optionLetter})
                                    </span>
                                    <span className="text-foreground flex-1">{option}</span>
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        )}
                        
                        {/* Open-ended answer area */}
                        {question.type === 'open-ended' && (
                          <div className="ml-8">
                            <textarea
                              value={userAnswers[question.number] || ''}
                              onChange={(e) => {
                                setUserAnswers(prev => ({
                                  ...prev,
                                  [question.number]: e.target.value
                                }));
                              }}
                              placeholder="Type your answer here..."
                              className="w-full min-h-[120px] p-3 rounded-lg border-2 border-border bg-background text-foreground focus:border-primary focus:outline-none resize-y"
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  
                  {/* Assessment Results */}
                  {assessmentResult && (
                    <div className="mt-8 p-6 rounded-lg bg-primary/5 border-2 border-primary/20 space-y-4">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xl font-bold text-foreground">Assessment Results</h3>
                        <Badge variant="default" className="text-lg px-4 py-2">
                          {assessmentResult.score}/{assessmentResult.total_questions} ({assessmentResult.percentage}%)
                        </Badge>
                      </div>
                      
                      {assessmentResult.study_recommendation && (
                        <div className="p-4 rounded-lg bg-background border border-border">
                          <h4 className="font-semibold text-foreground mb-2 flex items-center gap-2">
                            <Brain className="h-5 w-5 text-primary" />
                            Study Time Recommendation
                          </h4>
                          <p className="text-foreground/90 leading-relaxed">
                            {assessmentResult.study_recommendation}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Action buttons at the bottom */}
                  <div className="mt-8 pt-6 border-t border-border flex justify-end gap-2">
                    <Button 
                      variant="default" 
                      onClick={handleAssessExam} 
                      className="gap-2"
                      disabled={isAssessing || Object.keys(userAnswers).length === 0}
                    >
                      {isAssessing ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Assessing...
                        </>
                      ) : (
                        <>
                          <CheckCircle className="h-4 w-4" />
                          Assess Exam
                        </>
                      )}
                    </Button>
                    <Button variant="outline" onClick={handleExitExam} className="gap-2 hover:bg-destructive hover:text-destructive-foreground">
                      <X className="h-4 w-4" />
                      Exit Exam
                    </Button>
                  </div>
                  
                </Card>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                {assignments.map((assignment) => (
                  <AssignmentCard
                    key={assignment.id}
                    assignment={assignment}
                    isGenerating={examGeneratingFor === assignment.id}
                    hasExam={!!generatedExams[assignment.id]}
                    onStartExam={handleStartExam}
                    onViewExam={handleViewExam}
                  />
                ))}
              </div>
            )}

            {/* Remove the old exam loading overlay and error alert */}

            <Card className="bg-gradient-card border-border/50">
              <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-xl font-semibold">Latest Suggestions</h3>
                  <p className="text-sm text-muted-foreground">
                    Personalized study recommendations from the agent.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchSuggestions}
                    disabled={suggestionsLoading}
                  >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Refresh
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleResetSuggestions}
                    disabled={suggestionsLoading}
                  >
                    Reset
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleGenerateSuggestions}
                    disabled={suggestionsLoading}
                  >
                    <Sparkles className="mr-2 h-4 w-4" />
                    Generate
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {suggestionsError && (
                  <Alert variant="destructive">
                    <AlertDescription>{suggestionsError}</AlertDescription>
                  </Alert>
                )}
                {suggestionsLoading ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Fetching suggestions...
                  </div>
                ) : suggestions.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No suggestions yet. Generate a snapshot to see personalized
                    recommendations.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {suggestions.map((suggestion) => (
                      <div
                        key={suggestion.id}
                        className="rounded-lg border border-border/50 bg-background/60 p-4"
                      >
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <h4 className="font-semibold">{suggestion.title}</h4>
                            <p className="text-sm text-muted-foreground">
                              {suggestion.message}
                            </p>
                          </div>
                          <Badge variant="secondary">
                            {suggestion.priority?.toUpperCase() ?? "INFO"}
                          </Badge>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                          {suggestion.category && (
                            <span>Category: {suggestion.category}</span>
                          )}
                          {suggestion.status && (
                            <span>Status: {suggestion.status}</span>
                          )}
                          {suggestion.suggested_time_text && (
                            <span>
                              Suggested time: {suggestion.suggested_time_text}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="p-6">
        <div className="max-w-7xl mx-auto">
          {/* Stats Overview */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8 animate-slide-up">
              <Card className="p-4 bg-gradient-card border-border/50">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <BookOpen className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">3</p>
                    <p className="text-sm text-muted-foreground">
                      Active Tasks
                    </p>
                  </div>
                </div>
              </Card>

              <Card className="p-4 bg-gradient-card border-border/50">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-accent/10">
                    <Brain className="h-5 w-5 text-accent" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">12h</p>
                    <p className="text-sm text-muted-foreground">
                      Scheduled
                    </p>
                  </div>
                </div>
              </Card>

              <Card className="p-4 bg-gradient-card border-border/50">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-success/10">
                    <TrendingUp className="h-5 w-5 text-success" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">87%</p>
                    <p className="text-sm text-muted-foreground">
                      Avg Score
                    </p>
                  </div>
                </div>
              </Card>

              <Card className="p-4 bg-gradient-card border-border/50">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-warning/10">
                    <Calendar className="h-5 w-5 text-warning" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">5</p>
                    <p className="text-sm text-muted-foreground">
                      Days Until Exam
                    </p>
                  </div>
                </div>
              </Card>
            </div>

          {/* Main Content */}
          {renderMainContent()}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
