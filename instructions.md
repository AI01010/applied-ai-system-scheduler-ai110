# Show What You Know: Applied AI System

## ℹ️ Project Overview
> ⏰ ~4 hours

This final project is your opportunity to bring everything together, from debugging and design (Module 1-2) to reasoning and retrieval (Module 3-4), and finally agentic workflows and reliability testing (Module 5).

You'll choose one of your previous projects from Modules 1-3 and extend it into a full applied AI system that solves a meaningful problem or automates a reasoning task. This is your chance to evolve an earlier prototype into a polished, professional artifact.

Your system should demonstrate responsible design, technical creativity, and clear explanation of how the AI works and why it's trustworthy.


# 🎯 Goals

> By completing this project, you will be able to...

Extend and redesign a prior mini-project into a cohesive, end-to-end AI integrated system.
Implement modular components (retrieval, logic, or agentic planning) using Python.
Test and evaluate system reliability and guardrails through structured experiments.
Document and explain the AI's decision-making process clearly and responsibly.
Communicate results through a professional presentation and portfolio entry.
📊 Before you start, review the Grading Rubric to understand exactly how your project will be evaluated, including required features and optional stretch challenges worth extra points.

⚙️ Project Requirements
Your final project is about taking what you've already built and making it stronger, smarter, and more reliable. You'll extend one of your previous projects (from Modules 1-3) into a complete applied AI system.


## 💡 Example Extensions

Extension Idea	| Added AI Components
Add retrieval of external documentation and automated validation of answers	| RAG + testing + guardrails
Integrate agentic planning and error-logging into the existing workflow	| Agentic loop + logging
Extend explanation module with bias detection and evaluation metrics	| RAG + validation
Add reliability scoring or self-critique loop	| Testing + confidence scoring


# 0. Preparing Your Project Environment

Because this project is an evolution of your earlier work, you should create a dedicated copy of your chosen repo. This allows you to experiment freely without altering your original Module 1-3 submission.


Go to GitHub and create a new, public repo.

Name it something professional, like applied-ai-system-project.
Do not initialize it with a README, license, or .gitignore. Keep it completely empty.
Copy the URL of this new repo (e.g., https://github.com/username/applied-ai-system-final.git)

Clone your original repo into a new folder on your computer:

git clone https://github.com/username/your-original-repo.git applied-ai-system-final
Enter the folder: cd applied-ai-system-final

Update the remote to point to your new repo:

git remote set-url origin https://github.com/username/applied-ai-system-final.git

Push everything to your new repo:

git push -u origin main
Note: If your default branch is named master instead of main, use git push -u origin master.

Verify the connection: go to your new repo on GitHub and confirm your code and commit history are there.

Before you begin coding, set up a professional folder structure in your new repo.

Create a folder in your project called assets. This will be your dedicated directory for your system architecture images and screenshots.
If you are using Mermaid.js for your diagrams, be aware that free accounts are often limited to three charts. To avoid this limit, use the Mermaid Live Editor to build your diagram, then export it as a PNG and save it into your /assets folder.


# 1. Functionality: What Your System Should Do

> Your project should do something useful with AI. For example:

Summarize text or documents
Retrieve information or data from a source
Plan and complete a step-by-step task
Help debug, classify, or explain something
To make your project more advanced, it must include at least one of the following AI features:

Feature	What It Means	Example
Retrieval-Augmented Generation (RAG)	Your AI looks up or retrieves information before answering.	A study bot that searches notes before generating a quiz question.
Agentic Workflow	Your AI can plan, act, and check its own work.	A coding assistant that writes, tests, and then fixes code automatically.
Fine-Tuned or Specialized Model	You use a model that’s been trained or adjusted for a specific task.	A chatbot tuned to respond in a company’s tone of voice.
Reliability or Testing System	You include ways to measure or test how well your AI performs.	A script that checks if your AI gives consistent answers.
The feature should be fully integrated into the main application logic. It is not enough to have standalone script; the feature must meaningfully change how the system behaves or processes information. For example, if you add RAG, your AI should actively use the retrieved data to formulate its response rather than just printing the data alongside a standard answer.

Also, make sure your project:

Runs correctly and reproducibly: If someone follows your instructions, it should work.
Includes logging or guardrails: Your code should track what it does and handle errors safely.
Has clear setup steps: Someone else should be able to run it without guessing what to install.


# 2. Design and Architecture: How Your System Fits Together

> Show how your project is organized by creating a short system diagram. Your diagram should include:

The main components (like retriever, agent, evaluator, or tester).
How data flows through the system (input → process → output).
Where humans or testing are involved in checking AI results.


# 3. Documentation: How You Explain Your Work

> You'll write a README file that clearly explains your project. It should include:

Explicitly name your original project (from Modules 1-3) and provide a 2-3 sentence summary of its original goals and capabilities.
Title and Summary: What your project does and why it matters.
Architecture Overview: A short explanation of your system diagram.
Setup Instructions: Step-by-step directions to run your code.
Sample Interactions: Include at least 2-3 examples of inputs and the resulting AI outputs to demonstrate the system is functional.
Design Decisions: Why you built it this way, and what trade-offs you made.
Testing Summary: What worked, what didn't, and what you learned.
Reflection: What this project taught you about AI and problem-solving.
Write this for a future employer who might look at your GitHub portfolio! Clarity and completeness matter more than perfection.


# 4. Reliability and Evaluation: How You Test and Improve Your AI

> Your AI should prove that it works, not just seem like it does. Include at least one way to test or measure its reliability, such as:

Automated tests (e.g., unit tests or simple checks for key functions).
Confidence scoring (the AI rates how sure it is).
Logging and error handling (your code records what failed and why).
Human evaluation (you or a peer review the AI's output).
Summarize your testing in a few lines, like:

5 out of 6 tests passed; the AI struggled when context was missing. Confidence scores averaged 0.8; accuracy improved after adding validation rules.


# 5. Reflection and Ethics: Thinking Critically About Your AI

> AI isn't just about what works -- it's about what's responsible. Include a short reflection answering the following questions:

What are the limitations or biases in your system?
Could your AI be misused, and how would you prevent that?
What surprised you while testing your AI's reliability?
describe your collaboration with AI during this project. Identify one instance when the AI gave a helpful suggestion and one instance where its suggestion was flawed or incorrect.
🚀 Optional: Stretch Features for Extra Points
These features are completely optional and go beyond the required 21 points. Completing them can earn up to +8 additional points, allowing your score to exceed 100%. See the Grading Rubric for how each is evaluated.

Feature	What To Build	Points
RAG Enhancement	Extend your retrieval system to use custom documents or multiple data sources. Show how it measurably improves your AI's output quality.	+2
Agentic Workflow Enhancement	Implement multi-step reasoning with observable intermediate steps — tool-calls, planning steps, or a decision-making chain.	+2
Fine-Tuning or Specialization	Demonstrate specialized model behavior using few-shot patterns, synthetic datasets, or constrained tone/style. Show that output measurably differs from the baseline.	+2
Test Harness or Evaluation Script	Build a script that runs your system on a set of predefined inputs and prints a summary (pass/fail scores, confidence ratings, or similar).	+2
Note: These stretch features build directly on the required AI feature you chose in Step 1. For example, if you added RAG as your required feature, the RAG Enhancement stretch would extend that same component further.


# 6. Presentation and Portfolio: Sharing Your Work Professionally

> You'll wrap up by sharing your final project.

Prepare a 5-7 minute presentation showing your system, demo, and what you learned.
Add a portfolio artifact:
A GitHub link to your code
A short reflection paragraph: What this project says about me as an AI engineer.
Record a Loom video walkthrough (required): Create a short walkthrough showing your system running end-to-end. To record, we recommend using Loom. Include the link in your README.
[IMPORTANT]
To receive an accurate grade, please make sure your video walkthrough clearly demonstrates the following features:

✅ End-to-end system run (2–3 inputs)
✅ AI feature behavior (RAG, agent, etc.)
✅ Reliability/guardrail or evaluation behavior
✅ Clear outputs for each case
It does not need to show code setup, file structure, or installation steps.

If you are unsure about including something in your video, consult the Grading Rubric.


# 📬 Submitting Your Project

> Once you've completed all the required features for your project, use the following checklist to prepare your work for submission.

Code is pushed to the correct GitHub repository
Repo is public
Required files are present: You must include your functional code, a comprehensive README.md, a model_card.md for reflections, and a System Architecture Diagram (embedded in the README or as a separate image file).
Organized Assets: Your system diagram and any demo screenshots should be stored in a dedicated /assets or /diagrams folder within your repository.
Commit history shows multiple meaningful commits
Standardized Documentation: Your README.md must identify your base project, and your model_card.md must answer all reflection prompts regarding AI collaboration, biases, and testing results.
Demo walkthrough is included: Your README.md contains a Loom video link (or GIF/screenshot walkthrough) showing your system running end-to-end with at least 2-3 example inputs and AI responses.
Final changes are committed and pushed before the deadline