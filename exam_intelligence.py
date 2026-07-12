"""
exam_intelligence.py  —  ExamGuard-AI  |  Drop next to homepg.py
=================================================================
Two AI models in one file:

MODEL 1: Question Bank Randomizer
  - Teacher uploads 500 MCQ questions to a bank
  - System selects N random questions PER STUDENT (different set each time)
  - Prevents cheating via answer sharing between students
  - Guarantees topic coverage (category-balanced selection)
  - Generates unique exam_token per student so answers can't be compared

MODEL 2: Theory Answer Grader (NLP keyword + semantic similarity)
  - Teacher writes model answer + provides keywords
  - System grades student's text answer 0-100
  - Returns score + detailed explanation of what was right/wrong
  - Works WITHOUT external libraries (no sentence-transformers needed)
  - Uses TF-IDF cosine similarity + keyword coverage scoring
  - Can upgrade to sentence-transformers later for better accuracy
"""

import random
import math
import re
import string
import hashlib
from collections import Counter, defaultdict


# ══════════════════════════════════════════════════════════════════════════════
# MODEL 1 — QUESTION BANK RANDOMIZER
# ══════════════════════════════════════════════════════════════════════════════

class QuestionBankRandomizer:
    """
    Manages a pool of MCQ questions and generates unique randomized
    exams for each student to prevent answer sharing.

    Usage:
        bank = QuestionBankRandomizer(questions_list)
        student_exam = bank.generate_for_student("priya@gmail.com", n=60)
    """

    def __init__(self, questions: list):
        """
        Args:
            questions: List of dicts, each:
            {
                "id": "q001",                          # unique ID
                "question": "What is ...",             # question text
                "options": ["A","B","C","D"],          # 4 options
                "correct_index": 2,                    # 0-3
                "category": "Networks",                # topic tag (optional)
                "difficulty": "medium"                 # easy/medium/hard (optional)
            }
        """
        self.all_questions = questions
        self._build_index()

    def _build_index(self):
        """Build category and difficulty indexes for balanced selection."""
        self.by_category = defaultdict(list)
        self.by_difficulty = defaultdict(list)
        for q in self.all_questions:
            cat = q.get("category", "General")
            diff = q.get("difficulty", "medium")
            self.by_category[cat].append(q)
            self.by_difficulty[diff].append(q)

    def generate_for_student(self, student_email: str, n: int = 60,
                              seed_salt: str = "", balance_categories: bool = True,
                              difficulty_mix: dict = None) -> dict:
        """
        Generate a unique randomized exam for one student.

        Args:
            student_email   : Used as part of the random seed
            n               : Number of questions to select
            seed_salt       : Extra salt (e.g. exam_id) for uniqueness
            balance_categories : If True, pick proportionally from each category
            difficulty_mix  : e.g. {"easy": 0.2, "medium": 0.6, "hard": 0.2}
                              If None, selects randomly regardless of difficulty

        Returns:
            {
                "student_email": ...,
                "exam_token": ...,      # unique 8-char hex per student
                "questions": [...],     # selected questions (correct_index REMOVED for student view)
                "answer_key": {...},    # {question_id: correct_index} — server-side only
                "total": 60,
                "selection_method": "category_balanced" | "random"
            }
        """
        total_available = len(self.all_questions)
        if n > total_available:
            n = total_available

        # Deterministic but unique seed per student+exam
        seed_str = f"{student_email}:{seed_salt}:{n}"
        seed_int = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed_int)

        # Select questions
        if balance_categories and len(self.by_category) > 1:
            selected = self._balanced_select(rng, n, difficulty_mix)
        else:
            pool = self.all_questions.copy()
            if difficulty_mix:
                selected = self._difficulty_select(rng, pool, n, difficulty_mix)
            else:
                selected = rng.sample(pool, n)

        # Shuffle the options within each question (extra anti-cheat)
        # This means even if two students get the same question,
        # the correct answer is at a DIFFERENT option index for each
        student_questions = []
        answer_key = {}

        for q in selected:
            shuffled_q, new_correct = self._shuffle_options(q, rng)
            student_questions.append(shuffled_q)
            answer_key[shuffled_q["id"]] = new_correct

        # Shuffle question order too
        combined = list(zip(student_questions, [answer_key[q["id"]] for q in student_questions]))
        rng.shuffle(combined)
        student_questions = [c[0] for c in combined]
        answer_key = {q["id"]: c[1] for q, c in zip(student_questions, combined)}

        # Generate unique exam token for this student
        exam_token = hashlib.md5(seed_str.encode()).hexdigest()[:8].upper()

        # Remove correct_index from student-facing questions
        safe_questions = []
        for q in student_questions:
            sq = {k: v for k, v in q.items() if k != "correct_index"}
            safe_questions.append(sq)

        return {
            "student_email": student_email,
            "exam_token": exam_token,
            "questions": safe_questions,
            "answer_key": answer_key,       # NEVER send to student
            "total": len(safe_questions),
            "selection_method": "category_balanced" if balance_categories else "random",
            "categories_covered": list({q.get("category","General") for q in student_questions}),
        }

    def _balanced_select(self, rng, n, difficulty_mix):
        """Pick proportionally from each category."""
        categories = list(self.by_category.keys())
        per_cat = n // len(categories)
        remainder = n % len(categories)
        selected = []

        for i, cat in enumerate(categories):
            pool = self.by_category[cat].copy()
            pick = per_cat + (1 if i < remainder else 0)
            pick = min(pick, len(pool))
            if difficulty_mix:
                chosen = self._difficulty_select(rng, pool, pick, difficulty_mix)
            else:
                chosen = rng.sample(pool, pick)
            selected.extend(chosen)

        # If we still need more (due to small categories), fill from remaining
        if len(selected) < n:
            used_ids = {q["id"] for q in selected}
            remaining = [q for q in self.all_questions if q["id"] not in used_ids]
            extra = rng.sample(remaining, min(n - len(selected), len(remaining)))
            selected.extend(extra)

        return selected[:n]

    def _difficulty_select(self, rng, pool, n, difficulty_mix):
        """Select n questions matching difficulty distribution."""
        easy_pool   = [q for q in pool if q.get("difficulty","medium") == "easy"]
        medium_pool = [q for q in pool if q.get("difficulty","medium") == "medium"]
        hard_pool   = [q for q in pool if q.get("difficulty","medium") == "hard"]

        easy_n   = int(n * difficulty_mix.get("easy", 0.2))
        hard_n   = int(n * difficulty_mix.get("hard", 0.2))
        medium_n = n - easy_n - hard_n

        selected = []
        selected += rng.sample(easy_pool,   min(easy_n,   len(easy_pool)))
        selected += rng.sample(hard_pool,   min(hard_n,   len(hard_pool)))
        selected += rng.sample(medium_pool, min(medium_n, len(medium_pool)))

        # Fill any gaps
        if len(selected) < n:
            used = {q["id"] for q in selected}
            rest = [q for q in pool if q["id"] not in used]
            selected += rng.sample(rest, min(n - len(selected), len(rest)))

        return selected[:n]

    def _shuffle_options(self, q: dict, rng: random.Random):
        """
        Shuffle options within a question so same question has
        different correct_index for different students.
        Returns (shuffled_question_dict, new_correct_index).
        """
        options = q["options"].copy()
        correct_text = options[q["correct_index"]]

        # Create indexed shuffle
        indices = list(range(len(options)))
        rng.shuffle(indices)
        new_options = [options[i] for i in indices]
        new_correct = new_options.index(correct_text)

        shuffled = q.copy()
        shuffled["options"] = new_options
        shuffled["correct_index"] = new_correct
        return shuffled, new_correct

    def score_submission(self, answer_key: dict, student_answers: dict) -> dict:
        """
        Score a student's submission against the server-side answer key.

        Args:
            answer_key     : {question_id: correct_index}  (server side)
            student_answers: {question_id: selected_index} (from student)

        Returns:
            { score, total, percentage, per_question_results }
        """
        total = len(answer_key)
        correct = 0
        per_q = {}

        for qid, correct_idx in answer_key.items():
            student_idx = student_answers.get(qid)
            is_correct = (student_idx is not None and int(student_idx) == correct_idx)
            if is_correct:
                correct += 1
            per_q[qid] = {
                "correct": is_correct,
                "student_answer": student_idx,
                "correct_answer": correct_idx,
            }

        return {
            "score": correct,
            "total": total,
            "percentage": round(correct / total * 100, 1) if total else 0,
            "per_question": per_q,
        }

    def stats(self) -> dict:
        return {
            "total_questions": len(self.all_questions),
            "categories": {cat: len(qs) for cat, qs in self.by_category.items()},
            "by_difficulty": {d: len(qs) for d, qs in self.by_difficulty.items()},
        }


# ══════════════════════════════════════════════════════════════════════════════
# MODEL 2 — THEORY ANSWER GRADER
# ══════════════════════════════════════════════════════════════════════════════

class TheoryAnswerGrader:
    """
    Grades open-ended/theory student answers against a model answer.
    Works without any ML libraries using TF-IDF cosine similarity.

    Scoring is a weighted combination of:
      - Keyword coverage (40%): did student mention the required concepts?
      - Semantic similarity via TF-IDF cosine (40%): overall meaning match
      - Length adequacy (10%): is the answer detailed enough?
      - Structure bonus (10%): does it cover multiple points?

    Usage:
        grader = TheoryAnswerGrader()
        result = grader.grade(
            student_answer = "TCP uses three-way handshake...",
            model_answer   = "TCP establishes connection via SYN, SYN-ACK, ACK...",
            keywords       = ["SYN", "handshake", "reliable", "connection"],
            max_marks      = 10
        )
    """

    STOPWORDS = {
        "a","an","the","is","are","was","were","be","been","being","have","has",
        "had","do","does","did","will","would","could","should","may","might",
        "shall","must","can","to","of","in","on","at","by","for","with","about",
        "into","through","from","and","or","but","so","yet","nor","not","no",
        "this","that","these","those","it","its","i","we","you","he","she","they",
        "what","which","who","whom","when","where","why","how","all","each","every",
        "both","few","more","most","other","some","such","than","then","also",
    }

    def grade(self, student_answer: str, model_answer: str,
              keywords: list = None, max_marks: float = 10.0) -> dict:
        """
        Grade a student's theory answer.

        Args:
            student_answer : Student's written response
            model_answer   : Teacher's ideal answer
            keywords       : List of required concept words/phrases
            max_marks      : Maximum marks for this question

        Returns:
            {
                "marks_awarded": float,
                "max_marks": float,
                "percentage": float,
                "grade_label": "Excellent/Good/Adequate/Poor/Very Poor",
                "keyword_score": float (0-1),
                "similarity_score": float (0-1),
                "length_score": float (0-1),
                "keywords_found": [...],
                "keywords_missing": [...],
                "explanation": "Detailed feedback string",
                "strong_points": [...],
                "weak_points": [...],
            }
        """
        if not student_answer or not student_answer.strip():
            return self._empty_result(max_marks, "No answer provided.")

        s_clean = self._clean(student_answer)
        m_clean = self._clean(model_answer)

        # Component 1: Keyword coverage (40%)
        kw_result = self._keyword_score(s_clean, keywords or [])
        kw_score = kw_result["score"]

        # Component 2: TF-IDF cosine similarity (40%)
        sim_score = self._tfidf_cosine(s_clean, m_clean)

        # Component 3: Length adequacy (10%)
        len_score = self._length_score(student_answer, model_answer)

        # Component 4: Point coverage structure (10%)
        struct_score = self._structure_score(student_answer, model_answer)

        # Weighted total
        total_score = (kw_score * 0.40) + (sim_score * 0.40) + (len_score * 0.10) + (struct_score * 0.10)
        total_score = min(1.0, max(0.0, total_score))

        marks = round(total_score * max_marks, 1)
        pct = round(total_score * 100, 1)

        strong_points, weak_points = self._generate_feedback_points(
            kw_score, sim_score, len_score, struct_score,
            kw_result["found"], kw_result["missing"], student_answer, model_answer
        )

        explanation = self._build_explanation(
            marks, max_marks, pct,
            kw_score, sim_score, len_score, struct_score,
            kw_result["found"], kw_result["missing"]
        )

        return {
            "marks_awarded": marks,
            "max_marks": max_marks,
            "percentage": pct,
            "grade_label": self._grade_label(pct),
            "keyword_score": round(kw_score, 2),
            "similarity_score": round(sim_score, 2),
            "length_score": round(len_score, 2),
            "structure_score": round(struct_score, 2),
            "keywords_found": kw_result["found"],
            "keywords_missing": kw_result["missing"],
            "explanation": explanation,
            "strong_points": strong_points,
            "weak_points": weak_points,
        }

    def grade_batch(self, submissions: list) -> list:
        """
        Grade multiple student answers for the same question.
        submissions = [{"student": email, "answer": text}, ...]
        Returns list of grading results sorted by marks (highest first).
        """
        results = []
        for sub in submissions:
            result = self.grade(
                sub["answer"],
                sub.get("model_answer", ""),
                sub.get("keywords", []),
                sub.get("max_marks", 10.0)
            )
            result["student"] = sub.get("student", "unknown")
            results.append(result)
        return sorted(results, key=lambda x: x["marks_awarded"], reverse=True)

    # ── Internal methods ─────────────────────────────────────────────────────

    def _clean(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _tokenize(self, text: str) -> list:
        words = text.split()
        return [w for w in words if w not in self.STOPWORDS and len(w) > 2]

    def _keyword_score(self, student_clean: str, keywords: list) -> dict:
        if not keywords:
            return {"score": 0.5, "found": [], "missing": []}

        found = []
        missing = []
        for kw in keywords:
            kw_clean = kw.lower().strip()
            if kw_clean in student_clean:
                found.append(kw)
            else:
                # Try partial match for multi-word keywords
                words = kw_clean.split()
                if all(w in student_clean for w in words):
                    found.append(kw)
                else:
                    missing.append(kw)

        score = len(found) / len(keywords) if keywords else 0.5
        return {"score": score, "found": found, "missing": missing}

    def _tfidf_cosine(self, text_a: str, text_b: str) -> float:
        """TF-IDF cosine similarity between two texts."""
        tokens_a = self._tokenize(text_a)
        tokens_b = self._tokenize(text_b)

        if not tokens_a or not tokens_b:
            return 0.0

        # Build vocabulary
        vocab = list(set(tokens_a + tokens_b))

        # TF for each document
        tf_a = Counter(tokens_a)
        tf_b = Counter(tokens_b)

        # IDF (simple: log(2 / (1 + doc_count_with_term)) — only 2 docs)
        def tf_idf(tf, token, total):
            tf_val = tf.get(token, 0) / max(total, 1)
            in_both = 1 if (token in tf_a and token in tf_b) else 0
            idf = math.log(2 / (1 + in_both)) + 1
            return tf_val * idf

        total_a = len(tokens_a)
        total_b = len(tokens_b)

        vec_a = [tf_idf(tf_a, t, total_a) for t in vocab]
        vec_b = [tf_idf(tf_b, t, total_b) for t in vocab]

        # Cosine similarity
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a**2 for a in vec_a))
        mag_b = math.sqrt(sum(b**2 for b in vec_b))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return min(1.0, dot / (mag_a * mag_b))

    def _length_score(self, student: str, model: str) -> float:
        """
        Student answer should be at least 40% as long as the model answer.
        Penalize very short answers, reward adequately detailed ones.
        Don't reward for being longer than the model (verbosity != quality).
        """
        s_words = len(student.split())
        m_words = len(model.split())
        if m_words == 0:
            return 0.5
        ratio = s_words / m_words
        if ratio >= 0.8:   return 1.0
        if ratio >= 0.6:   return 0.8
        if ratio >= 0.4:   return 0.6
        if ratio >= 0.2:   return 0.3
        return 0.1

    def _structure_score(self, student: str, model: str) -> float:
        """
        Does the student cover multiple distinct points?
        Detects sentences/clauses — more structured answers score higher.
        """
        sentences_s = len(re.split(r'[.!?;]', student))
        sentences_m = len(re.split(r'[.!?;]', model))
        if sentences_m <= 1:
            return 1.0
        ratio = min(sentences_s / sentences_m, 1.0)
        return ratio

    def _grade_label(self, pct: float) -> str:
        if pct >= 85: return "Excellent"
        if pct >= 70: return "Good"
        if pct >= 50: return "Adequate"
        if pct >= 30: return "Poor"
        return "Very Poor"

    def _generate_feedback_points(self, kw_score, sim_score, len_score, struct_score,
                                   found, missing, student, model):
        strong = []
        weak = []

        if kw_score >= 0.8:
            strong.append(f"Covered {len(found)} key concept(s): {', '.join(found[:4])}")
        elif kw_score >= 0.5:
            strong.append(f"Mentioned {len(found)} relevant concept(s)")
        if missing:
            weak.append(f"Missing key concept(s): {', '.join(missing[:5])}")

        if sim_score >= 0.7:
            strong.append("Strong semantic alignment with the expected answer")
        elif sim_score >= 0.4:
            strong.append("Partial content overlap with expected answer")
        else:
            weak.append("Answer content differs significantly from expected explanation")

        if len_score >= 0.8:
            strong.append("Answer is adequately detailed")
        elif len_score < 0.4:
            weak.append("Answer is too brief — needs more elaboration")

        if struct_score >= 0.7:
            strong.append("Answer covers multiple points clearly")
        elif struct_score < 0.3:
            weak.append("Answer lacks structure — consider organizing into points")

        return strong, weak

    def _build_explanation(self, marks, max_marks, pct, kw_score, sim_score,
                            len_score, struct_score, found, missing):
        lines = [
            f"Score: {marks}/{max_marks} ({pct}%) — {self._grade_label(pct)}",
            "",
            f"• Keyword Coverage ({round(kw_score*100)}%): " +
            (f"Found: {', '.join(found)}. " if found else "No required keywords found. ") +
            (f"Missing: {', '.join(missing)}." if missing else "All keywords present."),
            "",
            f"• Content Similarity ({round(sim_score*100)}%): " +
            ("Strong match with expected answer." if sim_score>=0.7 else
             "Partial match." if sim_score>=0.4 else
             "Low overlap with expected answer."),
            "",
            f"• Answer Length ({round(len_score*100)}%): " +
            ("Well-detailed." if len_score>=0.8 else
             "Acceptable length." if len_score>=0.5 else
             "Too brief — expected more detail."),
            "",
            f"• Structure ({round(struct_score*100)}%): " +
            ("Well-structured with multiple points." if struct_score>=0.7 else
             "Could be better organized." if struct_score>=0.4 else
             "Very brief — single point only."),
        ]
        return "\n".join(lines)

    def _empty_result(self, max_marks, reason):
        return {
            "marks_awarded": 0.0, "max_marks": max_marks, "percentage": 0.0,
            "grade_label": "Very Poor",
            "keyword_score": 0.0, "similarity_score": 0.0,
            "length_score": 0.0, "structure_score": 0.0,
            "keywords_found": [], "keywords_missing": [],
            "explanation": reason,
            "strong_points": [], "weak_points": [reason],
        }


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("MODEL 1: Question Bank Randomizer")
    print("=" * 60)

    # Sample 10-question bank
    bank_questions = [
        {"id": f"q{i:03d}", "question": f"Question {i}?",
         "options": ["A","B","C","D"], "correct_index": i%4,
         "category": ["Networks","OS","DBMS","Security"][i%4],
         "difficulty": ["easy","medium","hard"][i%3]}
        for i in range(10)
    ]

    bank = QuestionBankRandomizer(bank_questions)
    print(f"Bank stats: {bank.stats()}")

    exam_priya = bank.generate_for_student("priya@gmail.com", n=5, seed_salt="exam001")
    exam_arjun = bank.generate_for_student("arjun@gmail.com", n=5, seed_salt="exam001")

    print(f"\nPriya's exam token: {exam_priya['exam_token']}")
    print(f"Arjun's exam token: {exam_arjun['exam_token']}")
    print(f"Same questions? {[q['id'] for q in exam_priya['questions']] == [q['id'] for q in exam_arjun['questions']]}")

    print("\n" + "=" * 60)
    print("MODEL 2: Theory Answer Grader")
    print("=" * 60)

    grader = TheoryAnswerGrader()
    result = grader.grade(
        student_answer="TCP uses a three-way handshake to establish a connection. The client sends SYN, server replies with SYN-ACK, then client sends ACK. This ensures reliable communication.",
        model_answer="TCP (Transmission Control Protocol) establishes a reliable connection using a three-way handshake process: the client sends a SYN packet, the server responds with SYN-ACK, and the client completes with ACK. This guarantees connection establishment before data transfer.",
        keywords=["SYN", "handshake", "reliable", "ACK", "TCP"],
        max_marks=10
    )
    print(f"\n{result['explanation']}")
    print(f"\nStrong points: {result['strong_points']}")
    print(f"Weak points:   {result['weak_points']}")