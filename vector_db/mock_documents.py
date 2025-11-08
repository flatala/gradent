"""Mock assignment documents for testing vector DB and RAG."""

MOCK_ASSIGNMENTS = {
    "rl_mdp_assignment": {
        "title": "Markov Decision Processes - Implementation",
        "course": "Reinforcement Learning",
        "content": """
# Assignment 1: Markov Decision Processes

## Overview
In this assignment, you will implement two fundamental algorithms for solving Markov Decision Processes (MDPs): Value Iteration and Policy Iteration. You will apply these algorithms to gridworld environments and analyze their performance.

## Learning Objectives
- Understand the Bellman equations and their role in MDP solution methods
- Implement value iteration from scratch
- Implement policy iteration from scratch
- Compare the convergence and computational efficiency of both algorithms
- Analyze how discount factor gamma affects optimal policies

## Background
A Markov Decision Process is defined by a tuple (S, A, P, R, γ) where:
- S is the set of states
- A is the set of actions
- P(s'|s,a) is the transition probability function
- R(s,a,s') is the reward function
- γ is the discount factor (0 ≤ γ < 1)

The goal is to find the optimal policy π* that maximizes expected cumulative discounted reward.

## Requirements

### Part 1: Value Iteration (40 points)
Implement the value iteration algorithm:

1. Initialize V(s) = 0 for all states
2. Repeat until convergence:
   - For each state s:
     V(s) = max_a Σ P(s'|s,a)[R(s,a,s') + γV(s')]
3. Extract optimal policy: π(s) = argmax_a Σ P(s'|s,a)[R(s,a,s') + γV(s')]

Convergence criterion: max_s |V_new(s) - V_old(s)| < θ where θ = 0.001

Your implementation should:
- Handle arbitrary gridworld sizes
- Support different reward structures
- Track number of iterations until convergence
- Visualize the optimal policy with arrows

### Part 2: Policy Iteration (40 points)
Implement the policy iteration algorithm:

1. Initialize π(s) arbitrarily for all states
2. Repeat until policy is stable:
   a. Policy Evaluation: Compute V^π(s) for current policy
   b. Policy Improvement: π'(s) = argmax_a Σ P(s'|s,a)[R(s,a,s') + γV^π(s')]
3. If π' = π, stop; else set π = π' and repeat

Your implementation should:
- Implement both synchronous and asynchronous policy evaluation
- Track number of policy improvements until convergence
- Compare efficiency with value iteration

### Part 3: Analysis (20 points)
Analyze your implementations on three gridworld problems:
1. Small gridworld (4x4) with goal state and obstacles
2. Cliff walking problem (4x12)
3. Large gridworld (10x10) with multiple rewards

For each problem, provide:
- Visualization of optimal policy
- Number of iterations until convergence
- Computational time
- Effect of varying gamma (test γ = 0.9, 0.95, 0.99)

## Deliverables
1. Python code (mdp_solver.py) with both algorithms
2. Jupyter notebook with experiments and visualizations
3. Written report (3-4 pages) analyzing results

## Grading Rubric
- Value Iteration Implementation: 40 points
  - Correct Bellman update: 20 points
  - Convergence check: 10 points
  - Policy extraction: 10 points
- Policy Iteration Implementation: 40 points
  - Policy evaluation: 20 points
  - Policy improvement: 15 points
  - Convergence detection: 5 points
- Analysis and Report: 20 points
  - Experimental results: 10 points
  - Comparison and insights: 10 points

## Hints
- Start with a small 3x3 gridworld to debug
- Use NumPy for efficient matrix operations
- Cache transition probabilities to avoid recomputation
- Visualize intermediate value functions to understand convergence
- Policy iteration typically converges in fewer iterations but each iteration is more expensive

## Prerequisites
You should be familiar with:
- Dynamic programming
- Markov chains
- Python and NumPy
- Basic probability theory

## Resources
- Sutton & Barto, Reinforcement Learning: An Introduction, Chapter 4
- CS7642 Lecture notes on MDPs
- Python MDP toolkit documentation

## Submission
Submit via Canvas by 11:59 PM on the due date. Late submissions lose 10% per day.
"""
    },
    
    "ml_supervised_learning": {
        "title": "Supervised Learning Analysis",
        "course": "Machine Learning",
        "content": """
# Assignment 1: Supervised Learning - Comparative Analysis

## Project Overview
This assignment requires you to implement and analyze five supervised learning algorithms on two datasets of your choice. The goal is to understand the strengths, weaknesses, and appropriate use cases for each algorithm.

## Algorithms to Implement

### 1. Decision Trees
- Implement ID3 or CART algorithm
- Support both classification and regression
- Tune max_depth and min_samples_split
- Analyze overfitting vs tree depth

### 2. Neural Networks
- Build feedforward neural network with backpropagation
- Use at least one hidden layer (experiment with architecture)
- Implement with PyTorch or TensorFlow
- Tune learning rate, batch size, epochs
- Use appropriate activation functions (ReLU, sigmoid)

### 3. Boosting (AdaBoost or Gradient Boosting)
- Implement ensemble of weak learners
- Tune number of estimators and learning rate
- Analyze how error decreases with ensemble size

### 4. Support Vector Machines (SVM)
- Implement with different kernels (linear, RBF, polynomial)
- Tune C (regularization) and kernel parameters
- Analyze decision boundaries
- Compare kernel performance

### 5. k-Nearest Neighbors (k-NN)
- Implement with different distance metrics
- Tune k (number of neighbors)
- Analyze effect of k on bias-variance tradeoff
- Consider curse of dimensionality

## Dataset Requirements

Choose TWO datasets:
1. One classification problem (e.g., image recognition, text classification)
2. One regression problem (e.g., housing prices, stock prediction)

Datasets should:
- Have at least 1000 samples
- Have at least 5 features
- Be publicly available or generated synthetically
- Present interesting challenges (class imbalance, non-linearity, etc.)

Suggested sources: UCI ML Repository, Kaggle, scikit-learn built-in datasets

## Experimental Methodology

For each algorithm on each dataset:

1. **Data Preprocessing**
   - Handle missing values
   - Normalize/standardize features
   - Encode categorical variables
   - Split into train/validation/test (60/20/20)

2. **Model Training**
   - Use k-fold cross-validation (k=5)
   - Tune hyperparameters via grid search or random search
   - Track training and validation curves

3. **Evaluation Metrics**
   - Classification: accuracy, precision, recall, F1-score, ROC-AUC
   - Regression: MSE, RMSE, MAE, R²
   - Report confusion matrices for classification
   - Analyze learning curves (training size vs performance)

4. **Computational Analysis**
   - Training time
   - Prediction time
   - Memory usage
   - Scalability with dataset size

## Deliverables

### 1. Code (40 points)
- Clean, well-documented Python code
- Use scikit-learn where appropriate
- Custom implementations for at least 2 algorithms
- Jupyter notebook with experiments

### 2. Written Report (60 points)
8-10 pages including:

**Section 1: Introduction (5 points)**
- Dataset descriptions
- Problem motivation

**Section 2: Methods (10 points)**
- Algorithm descriptions
- Implementation details
- Hyperparameter choices

**Section 3: Experiments (25 points)**
- Results tables comparing all algorithms
- Visualizations: learning curves, ROC curves, decision boundaries
- Statistical significance tests

**Section 4: Analysis (15 points)**
- Compare and contrast algorithm performance
- Discuss why certain algorithms work better
- Analyze failure cases
- Bias-variance tradeoff analysis

**Section 5: Conclusion (5 points)**
- Summary of findings
- Recommendations for practitioners
- Lessons learned

## Grading Breakdown

- Code quality and correctness: 25 points
- Experimental rigor: 15 points
- Results and visualizations: 20 points
- Analysis depth and insights: 25 points
- Writing clarity: 10 points
- Reproducibility: 5 points

## Tips for Success

1. **Start early** - This is a substantial project requiring 15-20 hours
2. **Choose interesting datasets** - Make the problem engaging
3. **Visualize everything** - Plots convey insights better than tables
4. **Be critical** - Don't just report numbers, explain WHY
5. **Compare fairly** - Use same train/test splits, same metrics
6. **Document assumptions** - Be transparent about choices made

## Common Pitfalls to Avoid

- Using test set for hyperparameter tuning (data leakage!)
- Not handling class imbalance
- Overfitting to validation set
- Cherry-picking results
- Insufficient cross-validation
- Poor feature scaling for algorithms that require it

## Prerequisites

- Understanding of supervised learning theory
- Python proficiency (NumPy, Pandas, Matplotlib)
- Familiarity with scikit-learn
- Basic statistics and hypothesis testing

## Resources

- Scikit-learn documentation and tutorials
- "Elements of Statistical Learning" by Hastie et al.
- CS7641 lecture slides and recordings
- Office hours: Wednesdays 2-4 PM

## Academic Integrity

You may discuss high-level concepts with classmates but all code and writing must be your own. Cite any external resources used.

## Due Date

Submit via Canvas by 11:59 PM, two weeks from today. This is a HARD deadline with no extensions except for documented emergencies.
"""
    },
    
    "cv_hybrid_images": {
        "title": "Image Filtering and Hybrid Images",
        "course": "Computer Vision",
        "content": """
# Project 1: Image Filtering and Hybrid Images

## Introduction

In this project, you will explore frequency domain image processing by implementing Gaussian and Laplacian pyramids and creating hybrid images - images that change appearance at different viewing distances.

Hybrid images are static images that change in interpretation as a function of viewing distance. The basic idea is that high frequency tends to dominate perception when an image is viewed from nearby, while low frequency dominates when the image is viewed from afar. By blending the high frequency portion of one image with the low-frequency portion of another, you get a hybrid image that leads to different interpretations at different viewing distances.

## Learning Goals

- Understand convolution and correlation in image processing
- Master frequency domain concepts (Fourier transform)
- Implement Gaussian and Laplacian pyramids
- Work with multi-scale image representations
- Explore human visual perception

## Part 1: Gaussian Pyramid (30 points)

Implement a function that constructs a Gaussian pyramid:

```python
def gaussian_pyramid(image, levels=5):
    '''
    Args:
        image: Input image (H x W x C)
        levels: Number of pyramid levels
    Returns:
        List of images at different scales
    '''
```

**Requirements:**
1. Use a Gaussian kernel (5x5, σ=1.0) for smoothing
2. Downsample by factor of 2 after each smoothing operation
3. Handle both grayscale and color images
4. Return list of progressively smaller images

**Implementation notes:**
- Use separable convolution for efficiency (convolve rows, then columns)
- Handle image boundaries appropriately (reflect padding recommended)
- Maintain proper data types to avoid overflow

## Part 2: Laplacian Pyramid (30 points)

Implement a function that constructs a Laplacian pyramid:

```python
def laplacian_pyramid(image, levels=5):
    '''
    Args:
        image: Input image
        levels: Number of pyramid levels
    Returns:
        List of Laplacian images and final Gaussian residual
    '''
```

The Laplacian pyramid is computed as:
L_i = G_i - expand(G_{i+1})

where expand() upsamples and smooths the smaller image to match the larger image size.

**Requirements:**
1. Build Gaussian pyramid first
2. For each level, compute difference with upsampled next level
3. Implement expand() function for upsampling
4. Verify pyramid can be reconstructed: image = sum of all Laplacian levels

## Part 3: Hybrid Images (40 points)

Create hybrid images by combining low and high frequencies from two aligned images:

```python
def create_hybrid_image(image1, image2, cutoff_low, cutoff_high):
    '''
    Args:
        image1: First input image (contributes low frequencies)
        image2: Second input image (contributes high frequencies)
        cutoff_low: Cutoff frequency for low-pass filter
        cutoff_high: Cutoff frequency for high-pass filter
    Returns:
        Hybrid image
    '''
```

**Algorithm:**
1. Apply low-pass filter to image1 (retain frequencies below cutoff_low)
2. Apply high-pass filter to image2 (retain frequencies above cutoff_high)
   - High-pass = image - low-pass version
3. Combine: hybrid = low_freq_image1 + high_freq_image2
4. Normalize and clip values to [0, 255]

**Suggested Image Pairs:**
- Cat and dog faces
- Einstein young and old
- Marilyn Monroe and Abraham Lincoln (classic example)
- Happy and sad faces
- Your own creative pairs!

**Tuning Cutoff Frequencies:**
- Start with cutoff_low = 7, cutoff_high = 15
- Experiment to find best values for your images
- Too high cutoff_low: low-freq image too blurry
- Too low cutoff_high: high-freq image too prominent

## Deliverables

### Code (40%)
Submit a single Python file `hybrid_images.py` containing:
- `gaussian_pyramid()`
- `laplacian_pyramid()`
- `create_hybrid_image()`
- Helper functions (filtering, upsampling, etc.)

### Report (60%)
PDF report (4-6 pages) with:

1. **Method Description** (10%)
   - Explain your implementation approach
   - Discuss design choices (kernel size, padding, etc.)

2. **Results** (30%)
   - Show Gaussian pyramid for at least one image (all levels)
   - Show Laplacian pyramid visualization
   - Show at least 3 hybrid images with:
     * Original image pair
     * Individual filtered components
     * Final hybrid image
     * FFT magnitude plots showing frequency content

3. **Analysis** (15%)
   - How do cutoff frequencies affect results?
   - What makes a good hybrid image pair?
   - Discuss failures and successes

4. **Extra Credit** (5%)
   - Implement color hybrid images (convert to different color space)
   - Create animated sequence showing pyramid levels
   - Implement image blending using Laplacian pyramids

## Grading Rubric

**Implementation (40 points)**
- Gaussian pyramid: 10 points
  - Correct convolution: 5 pts
  - Proper downsampling: 5 pts
- Laplacian pyramid: 10 points
  - Correct computation: 5 pts
  - Reconstruction works: 5 pts
- Hybrid images: 20 points
  - Low-pass filtering: 7 pts
  - High-pass filtering: 7 pts
  - Combination and normalization: 6 pts

**Report (60 points)**
- Clarity and completeness: 10 points
- Quality of results: 30 points
- Depth of analysis: 15 points
- Presentation and figures: 5 points

## Technical Requirements

- Use Python 3.x with NumPy and OpenCV
- Do NOT use built-in pyramid functions (cv2.pyrDown, etc.)
- Do NOT use built-in high-pass filters
- You MAY use cv2.GaussianBlur() for the Gaussian kernel
- All convolution must be implemented by you

## Hints

1. **Test on small images first** - Debugging is easier
2. **Visualize intermediate results** - Check filtered images look reasonable
3. **Use separable filters** - Much faster than 2D convolution
4. **Normalize carefully** - Hybrid images may need intensity adjustment
5. **Align images well** - Registration is critical for good hybrids
6. **Try different color channels** - Sometimes using only luminance works better

## Resources

- OpenCV Python tutorials
- "Computer Vision: Algorithms and Applications" by Szeliski, Chapter 3
- OLIVA, A., TORRALBA, A., AND SCHYNS, P. G. 2006. Hybrid images. ACM Transactions on Graphics 25, 3 (July), 527–530.

## Submission

Submit via Canvas:
- `hybrid_images.py` - Your implementation
- `report.pdf` - Your writeup with results
- `results/` - Folder with all output images

Due: 10 days from now, 11:59 PM
"""
    },
}


def get_mock_assignment_document(assignment_key: str) -> dict:
    """Get a mock assignment document by key.
    
    Args:
        assignment_key: Key from MOCK_ASSIGNMENTS
        
    Returns:
        Dictionary with title, course, and content
    """
    return MOCK_ASSIGNMENTS.get(assignment_key, {})


def get_all_mock_assignments() -> dict:
    """Get all mock assignment documents.
    
    Returns:
        Dictionary of all mock assignments
    """
    return MOCK_ASSIGNMENTS
