"""Mock Brightspace API client for testing and development.

In production, this would connect to the real Brightspace D2L API.
For now, it returns mock data that simulates API responses.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time


class MockBrightspaceClient:
    """Mock Brightspace API client that returns simulated course data.
    
    This simulates the Brightspace D2L API structure for:
    - Courses (organizational units)
    - Assignments (dropbox folders)
    - Content (course materials)
    - Announcements
    """
    
    def __init__(self, user_id: int = 1, api_key: Optional[str] = None):
        """Initialize mock client.
        
        Args:
            user_id: Student user ID
            api_key: API key (not used in mock, but would be required for real API)
        """
        self.user_id = user_id
        self.api_key = api_key
        self._mock_data_initialized = False
        self._initialize_mock_data()
    
    def _initialize_mock_data(self):
        """Initialize mock course data."""
        if self._mock_data_initialized:
            return
        
        now = datetime.now()
        
        # Mock courses
        self._courses = [
            {
                "OrgUnitId": 101,
                "Name": "Reinforcement Learning",
                "Code": "CS-7642",
                "StartDate": (now - timedelta(days=60)).isoformat(),
                "EndDate": (now + timedelta(days=60)).isoformat(),
                "IsActive": True,
            },
            {
                "OrgUnitId": 102,
                "Name": "Machine Learning",
                "Code": "CS-7641",
                "StartDate": (now - timedelta(days=50)).isoformat(),
                "EndDate": (now + timedelta(days=70)).isoformat(),
                "IsActive": True,
            },
            {
                "OrgUnitId": 103,
                "Name": "Computer Vision",
                "Code": "CS-6476",
                "StartDate": (now - timedelta(days=55)).isoformat(),
                "EndDate": (now + timedelta(days=65)).isoformat(),
                "IsActive": True,
            },
        ]
        
        # Mock assignments per course
        self._assignments = {
            101: [  # Reinforcement Learning
                {
                    "Id": 1001,
                    "Name": "[BRIGHTSPACE] Assignment 4: Reinforcement Learning",
                    "Instructions": {
                        "Text": "Implement value iteration and policy iteration algorithms for gridworld MDPs. Test on multiple environments and compare convergence rates.",
                        "Html": "<p>Implement value iteration and policy iteration for gridworld MDPs.</p>"
                    },
                    "DueDate": (now + timedelta(days=14)).isoformat(),
                    "TotalPoints": 100,
                    "IsHidden": False,
                    "SubmissionsRule": {
                        "SubmissionType": "File"
                    }
                },
                {
                    "Id": 1002,
                    "Name": "[BRIGHTSPACE] Project 3: Deep Q-Network on Atari",
                    "Instructions": {
                        "Text": "Train a Deep Q-Network agent on Atari games (Pong or Breakout). Implement experience replay and target networks. Analyze learning curves and performance.",
                        "Html": "<p>Train a DQN agent on Atari games.</p>"
                    },
                    "DueDate": (now + timedelta(days=28)).isoformat(),
                    "TotalPoints": 150,
                    "IsHidden": False,
                }
            ],
            102: [  # Machine Learning
                {
                    "Id": 2001,
                    "Name": "[BRIGHTSPACE] Project 1: Supervised Learning Comparison",
                    "Instructions": {
                        "Text": "Compare performance of decision trees, neural networks, boosting, SVM, and k-NN on two datasets. Use cross-validation and report detailed metrics.",
                        "Html": "<p>Compare ML algorithms on datasets.</p>"
                    },
                    "DueDate": (now + timedelta(days=21)).isoformat(),
                    "TotalPoints": 120,
                    "IsHidden": False,
                }
            ],
            103: [  # Computer Vision
                {
                    "Id": 3001,
                    "Name": "[BRIGHTSPACE] Assignment 2: Hybrid Images",
                    "Instructions": {
                        "Text": "Implement Gaussian and Laplacian pyramids. Create hybrid images using frequency domain filtering. Submit code, results, and analysis report.",
                        "Html": "<p>Image filtering assignment.</p>"
                    },
                    "DueDate": (now + timedelta(days=10)).isoformat(),
                    "TotalPoints": 80,
                    "IsHidden": False,
                }
            ]
        }
        
        # Mock course content/modules
        self._content = {
            101: [  # RL course materials
                {
                    "Id": 10001,
                    "Title": "Week 1: Introduction to MDPs",
                    "Type": "Module",
                    "Topics": [
                        {
                            "Id": 10101,
                            "Title": "Lecture 1 - MDP Fundamentals",
                            "Type": "File",
                            "Url": "https://mock-lms.edu/content/lecture1.pdf",
                            "Description": "Introduction to states, actions, transitions, and rewards"
                        },
                        {
                            "Id": 10102,
                            "Title": "Lecture 2 - Bellman Equations",
                            "Type": "File",
                            "Url": "https://mock-lms.edu/content/lecture2.pdf",
                            "Description": "Bellman optimality equations and dynamic programming"
                        }
                    ]
                },
                {
                    "Id": 10002,
                    "Title": "Week 2: Value and Policy Iteration",
                    "Type": "Module",
                    "Topics": [
                        {
                            "Id": 10201,
                            "Title": "Lecture 3 - Value Iteration",
                            "Type": "File",
                            "Url": "https://mock-lms.edu/content/lecture3.pdf",
                            "Description": "Value iteration algorithm and convergence"
                        }
                    ]
                }
            ],
            102: [  # ML course materials
                {
                    "Id": 20001,
                    "Title": "Module 1: Supervised Learning Basics",
                    "Type": "Module",
                    "Topics": [
                        {
                            "Id": 20101,
                            "Title": "Decision Trees Lecture",
                            "Type": "File",
                            "Url": "https://mock-lms.edu/ml/lecture1.pdf",
                            "Description": "Decision trees, entropy, and information gain"
                        }
                    ]
                }
            ]
        }
        
        # Mock announcements
        self._announcements = {
            101: [
                {
                    "Id": 5001,
                    "Title": "Assignment 1 Posted",
                    "Body": {
                        "Text": "The first assignment on MDPs is now available. Due in 2 weeks.",
                        "Html": "<p>The first assignment on MDPs is now available.</p>"
                    },
                    "StartDate": (now - timedelta(days=1)).isoformat(),
                    "IsImportant": True
                }
            ]
        }
        
        self._mock_data_initialized = True
    
    def get_enrollments(self) -> List[Dict[str, Any]]:
        """Get all course enrollments for the user.
        
        Returns:
            List of course enrollment objects
        """
        time.sleep(0.1)  # Simulate API latency
        return [
            {
                "OrgUnit": course,
                "Role": {"Name": "Student"},
                "Access": {"IsActive": True}
            }
            for course in self._courses
        ]
    
    def get_course(self, course_id: int) -> Optional[Dict[str, Any]]:
        """Get details for a specific course.
        
        Args:
            course_id: Brightspace organization unit ID
            
        Returns:
            Course details or None if not found
        """
        time.sleep(0.05)
        for course in self._courses:
            if course["OrgUnitId"] == course_id:
                return course
        return None
    
    def get_assignments(self, course_id: int) -> List[Dict[str, Any]]:
        """Get all assignments for a course.
        
        Args:
            course_id: Brightspace organization unit ID
            
        Returns:
            List of assignment objects
        """
        time.sleep(0.1)
        return self._assignments.get(course_id, [])
    
    def get_assignment(self, course_id: int, assignment_id: int) -> Optional[Dict[str, Any]]:
        """Get details for a specific assignment.
        
        Args:
            course_id: Brightspace organization unit ID
            assignment_id: Assignment ID
            
        Returns:
            Assignment details or None if not found
        """
        time.sleep(0.05)
        assignments = self._assignments.get(course_id, [])
        for assignment in assignments:
            if assignment["Id"] == assignment_id:
                return assignment
        return None
    
    def get_content_modules(self, course_id: int) -> List[Dict[str, Any]]:
        """Get content modules and materials for a course.
        
        Args:
            course_id: Brightspace organization unit ID
            
        Returns:
            List of content module objects
        """
        time.sleep(0.1)
        return self._content.get(course_id, [])
    
    def get_announcements(self, course_id: int) -> List[Dict[str, Any]]:
        """Get announcements for a course.
        
        Args:
            course_id: Brightspace organization unit ID
            
        Returns:
            List of announcement objects
        """
        time.sleep(0.05)
        return self._announcements.get(course_id, [])
    
    def download_file(self, file_url: str) -> str:
        """Download a file from Brightspace.
        
        Args:
            file_url: URL of the file to download
            
        Returns:
            Mock file content as text
        """
        time.sleep(0.2)  # Simulate download time
        
        # Return mock content based on URL
        if "lecture1" in file_url:
            return """
# Lecture 1: MDP Fundamentals

## What is a Markov Decision Process?

A Markov Decision Process (MDP) is a mathematical framework for modeling decision-making
in situations where outcomes are partly random and partly under the control of a decision maker.

## Components of an MDP

1. **States (S)**: The set of all possible situations
2. **Actions (A)**: The set of all possible decisions
3. **Transition Function P(s'|s,a)**: Probability of reaching state s' from state s via action a
4. **Reward Function R(s,a,s')**: Immediate reward received
5. **Discount Factor γ**: How much we value future rewards (0 < γ < 1)

## The Markov Property

The future is independent of the past given the present.
P(s_{t+1} | s_t, a_t, s_{t-1}, ..., s_0) = P(s_{t+1} | s_t, a_t)
"""
        elif "lecture2" in file_url:
            return """
# Lecture 2: Bellman Equations

## The Bellman Expectation Equation

V^π(s) = Σ_a π(a|s) Σ_{s'} P(s'|s,a)[R(s,a,s') + γV^π(s')]

## The Bellman Optimality Equation

V*(s) = max_a Σ_{s'} P(s'|s,a)[R(s,a,s') + γV*(s')]

This gives us the optimal value function, from which we can derive the optimal policy.
"""
        else:
            return f"Mock content for: {file_url}"


def get_brightspace_client(user_id: int = 1, api_key: Optional[str] = None) -> MockBrightspaceClient:
    """Get a Brightspace client instance.
    
    Args:
        user_id: Student user ID
        api_key: API key (for real API, not used in mock)
        
    Returns:
        Brightspace client instance
    """
    return MockBrightspaceClient(user_id=user_id, api_key=api_key)
