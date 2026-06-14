(function () {
  function shuffle(items) {
    const arr = [...items];
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function normalize(text) {
    return text
      .trim()
      .toLowerCase()
      .replace(/^to\s+/, "")
      .replace(/[.,;:!?"'()]/g, "")
      .trim();
  }

  function acceptableAnswers(answer) {
    return answer
      .toLowerCase()
      .split(/[,;/]|\s+or\s+/)
      .map((part) => normalize(part))
      .filter(Boolean);
  }

  function matchesAnswer(guess, answer, direction) {
    const g = direction === "en-to-ka" ? guess.trim() : normalize(guess);
    if (!g) return false;
    if (direction === "en-to-ka") {
      return g === answer.trim();
    }
    return acceptableAnswers(answer).some((part) => g === part);
  }

  window.ThemeQuiz = {
    init({ themeId, words, audioBase = "../" }) {
      const overlay = document.getElementById("quiz-overlay");
      const openBtn = document.getElementById("quiz-open");
      if (!overlay || !openBtn) return;

      const promptEl = document.getElementById("quiz-prompt");
      const subEl = document.getElementById("quiz-sub");
      const inputEl = document.getElementById("quiz-input");
      const feedbackEl = document.getElementById("quiz-feedback");
      const progressEl = document.getElementById("quiz-progress");
      const checkBtn = document.getElementById("quiz-check");
      const nextBtn = document.getElementById("quiz-next");
      const closeBtn = document.getElementById("quiz-close");
      const playBtn = document.getElementById("quiz-play");
      const modeKaBtn = document.getElementById("quiz-mode-ka");
      const modeEnBtn = document.getElementById("quiz-mode-en");
      const resultEl = document.getElementById("quiz-result");
      const quizBody = document.getElementById("quiz-body");

      let direction = "ka-to-en";
      let queue = [];
      let index = 0;
      let score = 0;
      let answered = false;
      let currentAudio = null;

      function setMode(mode) {
        direction = mode;
        modeKaBtn.classList.toggle("active", mode === "ka-to-en");
        modeEnBtn.classList.toggle("active", mode === "en-to-ka");
      }

      function pickQueue() {
        const pool = words.filter((w) => w.en && w.ka);
        const n = Math.min(10, pool.length);
        return shuffle(pool).slice(0, n);
      }

      function currentWord() {
        return queue[index];
      }

      function resetInput() {
        answered = false;
        inputEl.value = "";
        inputEl.disabled = false;
        feedbackEl.textContent = "";
        feedbackEl.className = "quiz-feedback";
        checkBtn.style.display = "inline-block";
        nextBtn.style.display = "none";
        inputEl.focus();
      }

      function showQuestion() {
        resultEl.style.display = "none";
        quizBody.style.display = "block";
        const w = currentWord();
        if (!w) return;

        progressEl.textContent = `question ${index + 1} / ${queue.length}`;
        playBtn.disabled = !w.audio;

        if (direction === "ka-to-en") {
          promptEl.textContent = w.ka;
          promptEl.className = "quiz-prompt ka";
          subEl.textContent = [w.roman, w.pos].filter(Boolean).join(" · ");
          inputEl.placeholder = "type the english meaning";
        } else {
          promptEl.textContent = w.en;
          promptEl.className = "quiz-prompt";
          subEl.textContent = w.pos || "";
          inputEl.placeholder = "type the georgian word";
        }
        resetInput();
      }

      function showResult() {
        quizBody.style.display = "none";
        resultEl.style.display = "block";
        resultEl.innerHTML = `
          <div class="quiz-score">${score} / ${queue.length}</div>
          <p class="quiz-score-label">correct</p>
          <button class="action-btn accent" id="quiz-retry">try again</button>
        `;
        document.getElementById("quiz-retry").addEventListener("click", startQuiz);
      }

      function startQuiz() {
        queue = pickQueue();
        if (!queue.length) return;
        index = 0;
        score = 0;
        overlay.classList.add("open");
        showQuestion();
      }

      function checkAnswer() {
        if (answered) return;
        const w = currentWord();
        const guess = inputEl.value;
        const ok = matchesAnswer(guess, w.en, direction === "ka-to-en" ? "ka-to-en" : "en-to-ka")
          || (direction === "en-to-ka" && guess.trim() === w.ka);

        answered = true;
        if (ok) {
          score += 1;
          feedbackEl.textContent = "correct";
          feedbackEl.className = "quiz-feedback ok";
        } else {
          const shown = direction === "ka-to-en" ? w.en : w.ka;
          feedbackEl.textContent = `not quite — ${shown}`;
          feedbackEl.className = "quiz-feedback miss";
        }
        inputEl.disabled = true;
        checkBtn.style.display = "none";
        nextBtn.style.display = "inline-block";
      }

      function nextQuestion() {
        if (index + 1 >= queue.length) {
          showResult();
          return;
        }
        index += 1;
        showQuestion();
      }

      openBtn.addEventListener("click", startQuiz);
      closeBtn.addEventListener("click", () => overlay.classList.remove("open"));
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) overlay.classList.remove("open");
      });
      checkBtn.addEventListener("click", checkAnswer);
      nextBtn.addEventListener("click", nextQuestion);
      inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          if (!answered) checkAnswer();
          else nextQuestion();
        }
      });
      modeKaBtn.addEventListener("click", () => setMode("ka-to-en"));
      modeEnBtn.addEventListener("click", () => setMode("en-to-ka"));
      playBtn.addEventListener("click", () => {
        const w = currentWord();
        if (!w || !w.audio) return;
        if (currentAudio) currentAudio.pause();
        const src = w.audio.startsWith("http") ? w.audio : audioBase + w.audio;
        currentAudio = new Audio(src);
        currentAudio.play().catch(() => {});
      });

      setMode("ka-to-en");
      openBtn.disabled = words.length < 4;
      openBtn.title = words.length < 4 ? "need at least 4 words" : "quiz 10 words";
    },
  };
})();
