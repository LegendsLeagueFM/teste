const QUESTIONS_DATA_URL = 'data/mp_questions.json';
const LAST_QUESTION_KEY = 'mpgo-last-question-id';
const USED_QUESTIONS_KEY = 'mpgo-used-question-ids';

function formatMeta(question) {
    const parts = [];
    if (question.exam) parts.push(question.exam);
    if (question.bank) parts.push(`Banca: ${question.bank}`);
    if (question.year) parts.push(question.year);
    if (question.theme) parts.push(question.theme);
    return parts.join(' • ');
}

function pickQuestion(questions, lastId, usedSet) {
    if (!questions.length) return null;
    const prioritized = questions.filter((q) => q.state === 'GO');
    const pool = prioritized.length ? prioritized : questions;
    if (pool.length === 1) return pool[0];

    const availablePool = pool.filter((q) => !usedSet.has(q.id));
    const candidates = availablePool.length ? availablePool : pool;
    if (!availablePool.length) usedSet.clear();

    let candidate = null;
    let attempts = 0;
    do {
        candidate = candidates[Math.floor(Math.random() * candidates.length)];
        attempts += 1;
    } while (candidate.id === lastId && attempts < 5);

    usedSet.add(candidate.id);
    return candidate;
}

function renderQuestion(question, elements) {
    const { textEl, metaEl, optionsEl, feedbackEl } = elements;
    textEl.textContent = question.question;
    metaEl.textContent = formatMeta(question);
    feedbackEl.textContent = '';
    feedbackEl.className = 'question-feedback';

    optionsEl.innerHTML = '';
    question.options.forEach((optionText, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'question-option';
        button.textContent = optionText;
        button.addEventListener('click', () => handleAnswer(button, index, question, elements));
        optionsEl.appendChild(button);
    });
}

function handleAnswer(button, chosenIndex, question, elements) {
    const { optionsEl, feedbackEl } = elements;
    const buttons = Array.from(optionsEl.querySelectorAll('.question-option'));
    buttons.forEach((btn) => {
        btn.disabled = true;
        btn.classList.add('question-option--disabled');
    });

    const correctButton = buttons[question.answer];
    if (correctButton) correctButton.classList.add('question-option--correct');

    if (chosenIndex === question.answer) {
        button.classList.add('question-option--selected');
        feedbackEl.textContent = 'Resposta correta!';
        feedbackEl.classList.add('question-feedback--success');
    } else {
        button.classList.add('question-option--selected');
        feedbackEl.textContent = 'Não foi desta vez. Reveja o comentário e tente outra questão.';
        feedbackEl.classList.add('question-feedback--error');
    }

    const comment = document.createElement('div');
    comment.className = 'question-comment';
    comment.textContent = `${question.reference} — ${question.comment}`;
    feedbackEl.appendChild(comment);
}

function setLoadingState(elements, message) {
    const { textEl, metaEl, optionsEl, feedbackEl } = elements;
    textEl.textContent = message;
    metaEl.textContent = '';
    feedbackEl.textContent = '';
    optionsEl.innerHTML = '';
}

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('mpgo-question');
    if (!container) return;

    const elements = {
        textEl: container.querySelector('[data-question-text]'),
        metaEl: container.querySelector('[data-question-meta]'),
        optionsEl: container.querySelector('[data-question-options]'),
        feedbackEl: container.querySelector('[data-question-feedback]'),
    };

    const actionButton = container.querySelector('[data-new-question]');
    if (!actionButton) return;

    const setButtonLoading = (isLoading) => {
        actionButton.disabled = isLoading;
        actionButton.classList.toggle('question-refresh--loading', isLoading);
        actionButton.textContent = isLoading ? 'Carregando...' : 'Gerar outra questão';
    };

    let cachedQuestions = [];
    let lastQuestionId = localStorage.getItem(LAST_QUESTION_KEY);
    let usedQuestionIds = new Set();

    try {
        const storedUsed = localStorage.getItem(USED_QUESTIONS_KEY);
        usedQuestionIds = storedUsed ? new Set(JSON.parse(storedUsed)) : new Set();
    } catch (error) {
        usedQuestionIds = new Set();
    }

    const loadAndRender = () => {
        setButtonLoading(true);
        if (!cachedQuestions.length) {
            setLoadingState(elements, 'Carregando questões recentes dos MPs estaduais...');
            fetch(QUESTIONS_DATA_URL)
                .then((response) => response.json())
                .then((data) => {
                    cachedQuestions = Array.isArray(data) ? data : [];
                    const question = pickQuestion(cachedQuestions, lastQuestionId, usedQuestionIds);
                    if (question) {
                        renderQuestion(question, elements);
                        lastQuestionId = question.id;
                        localStorage.setItem(USED_QUESTIONS_KEY, JSON.stringify(Array.from(usedQuestionIds)));
                        localStorage.setItem(LAST_QUESTION_KEY, lastQuestionId);
                    } else {
                        setLoadingState(elements, 'Nenhuma questão disponível no momento.');
                    }
                })
                .catch(() => {
                    setLoadingState(elements, 'Não foi possível carregar as questões. Verifique sua conexão ou tente novamente.');
                })
                .finally(() => {
                    setButtonLoading(false);
                });
        } else {
            const question = pickQuestion(cachedQuestions, lastQuestionId, usedQuestionIds);
            if (question) {
                renderQuestion(question, elements);
                lastQuestionId = question.id;
                localStorage.setItem(USED_QUESTIONS_KEY, JSON.stringify(Array.from(usedQuestionIds)));
                localStorage.setItem(LAST_QUESTION_KEY, lastQuestionId);
            }
            setButtonLoading(false);
        }
    };

    actionButton.addEventListener('click', loadAndRender);
    setButtonLoading(true);
    loadAndRender();
});
