import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Clock, ChevronRight, Pause } from "lucide-react";

const mockQuestions = [
  {
    id: 1,
    question: "What is an eigenvalue?",
    options: [
      "A scalar that transforms a vector's magnitude only",
      "A vector that remains unchanged under transformation",
      "A matrix diagonal element",
      "The determinant of a matrix",
    ],
    correctAnswer: 0,
  },
  {
    id: 2,
    question: "Which operation is NOT associative?",
    options: [
      "Matrix multiplication",
      "Matrix addition",
      "Matrix subtraction",
      "Scalar multiplication",
    ],
    correctAnswer: 2,
  },
  {
    id: 3,
    question: "What defines a vector space?",
    options: [
      "Only addition operation",
      "Only scalar multiplication",
      "Closed under addition and scalar multiplication",
      "Contains the zero vector only",
    ],
    correctAnswer: 2,
  },
];

interface MockExamProps {
  assignment: any;
  onComplete: (results: any) => void;
}

const MockExam = ({ assignment, onComplete }: MockExamProps) => {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [timeRemaining, setTimeRemaining] = useState(30 * 60); // 30 minutes
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    if (isPaused) return;

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 0) {
          handleComplete();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isPaused]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const handleAnswer = (questionId: number, answerIndex: number) => {
    setAnswers({ ...answers, [questionId]: answerIndex });
  };

  const handleNext = () => {
    if (currentQuestion < mockQuestions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    }
  };

  const handleComplete = () => {
    const score = mockQuestions.reduce((acc, question) => {
      return acc + (answers[question.id] === question.correctAnswer ? 1 : 0);
    }, 0);

    const results = {
      score: Math.round((score / mockQuestions.length) * 100),
      totalQuestions: mockQuestions.length,
      correctAnswers: score,
      weakTopics: ["Eigenvalues", "Vector Spaces"],
      assignment: assignment,
    };

    onComplete(results);
  };

  const progress = ((currentQuestion + 1) / mockQuestions.length) * 100;
  const question = mockQuestions[currentQuestion];

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-3xl p-8 shadow-lg animate-fade-in">
        {/* Header */}
        <div className="mb-8 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">{assignment.title}</h2>
              <p className="text-muted-foreground">Mock Examination</p>
            </div>
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsPaused(!isPaused)}
              >
                <Pause className="h-4 w-4 mr-2" />
                {isPaused ? "Resume" : "Pause"}
              </Button>
              <div className="flex items-center gap-2 px-4 py-2 bg-muted rounded-lg">
                <Clock className="h-5 w-5 text-primary" />
                <span className="font-mono text-lg font-semibold">
                  {formatTime(timeRemaining)}
                </span>
              </div>
            </div>
          </div>

          {/* Progress */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Question {currentQuestion + 1} of {mockQuestions.length}
              </span>
              <span className="font-medium">
                {Math.round(progress)}% Complete
              </span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        </div>

        {/* Question */}
        <div className="space-y-6 mb-8">
          <div className="p-6 bg-muted rounded-lg">
            <h3 className="text-xl font-semibold leading-relaxed">
              {question.question}
            </h3>
          </div>

          {/* Options */}
          <RadioGroup
            value={answers[question.id]?.toString()}
            onValueChange={(value) =>
              handleAnswer(question.id, parseInt(value))
            }
            className="space-y-3"
          >
            {question.options.map((option, index) => (
              <div
                key={index}
                className="flex items-center space-x-3 p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors cursor-pointer"
              >
                <RadioGroupItem
                  value={index.toString()}
                  id={`option-${index}`}
                />
                <Label
                  htmlFor={`option-${index}`}
                  className="flex-1 cursor-pointer text-base"
                >
                  {option}
                </Label>
              </div>
            ))}
          </RadioGroup>
        </div>

        {/* Actions */}
        <div className="flex justify-between">
          <Button
            variant="outline"
            disabled={currentQuestion === 0}
            onClick={() => setCurrentQuestion(currentQuestion - 1)}
          >
            Previous
          </Button>

          {currentQuestion === mockQuestions.length - 1 ? (
            <Button onClick={handleComplete} size="lg" className="shadow-md">
              Complete Exam
            </Button>
          ) : (
            <Button
              onClick={handleNext}
              size="lg"
              disabled={answers[question.id] === undefined}
              className="shadow-md"
            >
              Next Question
              <ChevronRight className="ml-2 h-5 w-5" />
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
};

export default MockExam;
