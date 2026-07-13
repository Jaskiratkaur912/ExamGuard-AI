/**
 * ML Service — Frontend API integration
 * Handle all ML-related API calls
 * Save as: static/js/ml-service.js
 */

class MLService {
    constructor(token) {
        this.token = token;
        this.apiBase = '/api/ml';
    }

    /**
     * Get cheating analysis for a submission
     */
    async getCheatingAnalysis(submissionId) {
        return this.fetch(`/cheating-analysis/${submissionId}`, 'GET');
    }

    /**
     * Create/run cheating analysis on a submission
     */
    async analyzeCheating(submissionId, violationLog = null) {
        return this.fetch(`/cheating-analysis/create/${submissionId}`, 'POST', {
            violation_log: violationLog
        });
    }

    /**
     * Get cheating summary for all submissions in an exam
     */
    async getExamCheatingReport(examId) {
        return this.fetch(`/cheating-analysis/exam/${examId}`, 'GET');
    }

    /**
     * Get or create randomized exam for student
     */
    async getRandomizedExam(examId, submissionId = null) {
        return this.fetch('/randomized-exams', 'POST', {
            exam_id: examId,
            submission_id: submissionId
        });
    }

    /**
     * Get exam variant details
     */
    async getExamVariant(variantId) {
        return this.fetch(`/randomized-exams/${variantId}`, 'GET');
    }

    /**
     * Get exam variant for student (teacher access)
     */
    async getStudentExamVariant(examId, studentId) {
        return this.fetch(`/randomized-exams/exam/${examId}/student/${studentId}`, 'GET');
    }

    /**
     * Get randomization stats for exam
     */
    async getExamRandomizationStats(examId) {
        return this.fetch(`/randomized-exams/exam/${examId}/stats`, 'GET');
    }

    /**
     * Grade a single answer using keyword analysis
     */
    async gradeAnswer(answerId, modelAnswer = null, expectedKeywords = null) {
        return this.fetch(`/grade-answer/${answerId}`, 'POST', {
            model_answer: modelAnswer,
            expected_keywords: expectedKeywords
        });
    }

    /**
     * Grade all answers in a submission
     */
    async gradeSubmission(submissionId) {
        return this.fetch(`/grade-submission/${submissionId}`, 'POST', {});
    }

    /**
     * Get keyword analysis for an answer
     */
    async getAnswerAnalysis(answerId) {
        return this.fetch(`/answer-analysis/${answerId}`, 'GET');
    }

    /**
     * Get all analyses for a submission
     */
    async getSubmissionAnalysis(submissionId) {
        return this.fetch(`/submission-analysis/${submissionId}`, 'GET');
    }

    /**
     * Get comprehensive submission report
     * Perfect for dashboard!
     */
    async getComprehensiveReport(submissionId) {
        return this.fetch(`/submission-report/${submissionId}`, 'GET');
    }

    /**
     * Internal fetch helper
     */
    async fetch(endpoint, method, data = null) {
        const options = {
            method,
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(`${this.apiBase}${endpoint}`, options);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('ML Service Error:', error);
            throw error;
        }
    }
}

/**
 * Initialize ML Service
 * Usage: const ml = new MLService(localStorage.getItem('token'));
 */

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MLService;
}
