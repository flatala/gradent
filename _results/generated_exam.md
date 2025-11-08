### Midterm Exam: Recommender Systems  
**Course Code:** CS-456  
**Date:** [Insert Date]  
**Time Allowed:** 1.5 Hours  
**Total Marks:** 100  

---

**Instructions for Candidates:**  
1. This exam consists of **10 multiple-choice questions (MCQs)**.  
2. Each question carries **10 marks**.  
3. Read each question carefully and select the **most appropriate option**.  
4. Answer all questions in the designated answer sheet or space provided.  
5. No calculators or external resources are allowed.  

---

### **Section A: Multiple Choice Questions (MCQs)**  
**Difficulty Level: Easy (Questions 1–3, 6–7), Medium (Question 8, 4–5), Hard (Questions 9–10)**  

---

**1. (Easy – 10 marks)**  
What is the primary purpose of the Low-rank Neighborhood Model in recommender systems?  
A) To replace the similarity matrix **S** with two low-dimensional matrices **U** and **V**  
B) To increase computational complexity  
C) To eliminate the need for user-item interactions  
D) To prioritize popular items over less popular ones  
**Correct Answer: A**  

---

**2. (Easy – 10 marks)**  
In the Low-rank Neighborhood Model, what does the parameter **k** represent?  
A) Number of users  
B) Number of items  
C) Dimensionality of the low-rank matrices **U** and **V**  
D) The size of the original similarity matrix  
**Correct Answer: C**  

---

**3. (Easy – 10 marks)**  
Which of the following is a key advantage of the Low-rank Neighborhood Model over SLIM and EASE?  
A) Faster computation of the similarity matrix  
B) Reduced memory required to store model parameters  
C) Elimination of popularity bias  
D) Dynamic updating of the model with new data  
**Correct Answer: B**  

---

**4. (Medium – 10 marks)**  
What is the main computational challenge of updating the similarity matrix in traditional models?  
A) It requires recalculating the entire matrix for new observations  
B) It increases the dimensionality of **k**  
C) It introduces position bias  
D) It reduces model accuracy  
**Correct Answer: A**  

---

**5. (Medium – 10 marks)**  
Why is the constraint **diag(UV^T) = 0** imposed in the Low-rank Neighborhood Model?  
A) To ensure the matrices **U** and **V** are orthogonal  
B) To prevent self-similarity in the predicted similarity matrix  
C) To reduce the value of **k**  
D) To enforce sparsity in the model  
**Correct Answer: B**  

---

**6. (Easy – 10 marks)**  
Which model improves computational complexity over SLIM?  
A) ItemKNN  
B) Low-rank Neighborhood Model  
C) EASE (Embarrassingly Shallow Auto-Encoders)  
D) Cascading Bandits  
**Correct Answer: C**  

---

**7. (Easy – 10 marks)**  
If **n = 1M** (users/items) and **k = 10**, what is the approximate memory required for matrices **U** and **V** in the Low-rank Neighborhood Model?  
A) 0.08 GB  
B) 0.8 GB  
C) 8 GB  
D) 80 GB  
**Correct Answer: A**  

---

**8. (Medium – 10 marks)**  
Which of the following is a limitation of models that rely on similarity matrices?  
A) They are immune to popularity bias  
B) Updating with new data requires recalculating the entire matrix  
C) They always use high-dimensional matrices  
D) They cannot handle dynamic environments  
**Correct Answer: B**  

---

**9. (Hard – 10 marks)**  
What is the mathematical formulation of the Low-rank Neighborhood Model's optimization problem?  
A) **min_{U,V} ||R - UV^T||_F^2 + λ||U||_F^2 + λ||V||_F^2**  
B) **min_{U,V} ||R - UV^T||_F^2 + λ||U^T V||_F^2**  
C) **min_{U,V} ||R - UV^T||_F^2 + λ||U + V||_F^2**  
D) **min_{U,V} ||R - UV^T||_F^2 + λ||U - V||_F^2**  
**Correct Answer: A**  

---

**10. (Hard – 10 marks)**  
Which of the following is NOT a type of bias mentioned in the context of recommender systems?  
A) Popularity bias  
B) Position bias  
C) Temporal bias  
D) Diversity bias  
**Correct Answer: C**  

---

### **Section B: Answers**  
**Answer Key**  
1. **A**  
2. **C**  
3. **B**  
4. **A**  
5. **B**  
6. **C**  
7. **A**  
8. **B**  
9. **A**  
10. **C**  

---  
**End of Exam**  

---  
*Note: This exam paper is designed to assess understanding of key concepts in recommender systems, including model optimization, computational challenges, and bias in recommendations.*