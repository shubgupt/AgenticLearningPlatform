function canvasApp() {
  return {
    loading: true,
    lesson: null,
    currentStepIndex: 0,
    attempts: 0,
    xp: 0,
    xpBumped: false,
    answered: false,
    showHint: false,
    showCorrectModal: false,
    listening: false,
    zoneToast: '',
    zoneToastTimer: null,
    elapsedSeconds: 0,
    timerHandle: null,

    // 'canvas' = the normal lesson view; 'request' = the generate-a-lesson form
    view: 'canvas',
    modalityOptions: ['Concepts-First', 'Examples-First', 'Socratic Questioning', 'Flipped Analogy', 'Code-First', 'Story-Based'],
    requestForm: { skill: '', modality: 'Story-Based', name: '', age: '', grade: '', favorite_sport: '' },
    requestStatus: null, // null | 'pending' | 'generating' | 'ready' | 'failed'
    requestError: '',
    requestPollHandle: null,

    // Lesson-level character pick (persists across steps)
    selectedCharacterId: null,

    // Per-step interactive state
    controlValues: {},
    objectPositions: {},
    slideIndex: 0,
    storyIndex: 0,

    // Evaluation input state
    selectedOptionId: null,
    freeTextAnswer: '',
    freeTextWrong: false,
    dropdownAnswer: '',
    dropdownWrong: false,

    get currentStep() {
      return this.lesson?.steps?.[this.currentStepIndex] || null;
    },

    get formattedTime() {
      const m = Math.floor(this.elapsedSeconds / 60).toString().padStart(2, '0');
      const s = (this.elapsedSeconds % 60).toString().padStart(2, '0');
      return `${m}:${s}`;
    },

    get selectedCharacter() {
      return this.lesson?.character_library?.find(c => c.id === this.selectedCharacterId) || null;
    },

    get hasNetForceReadout() {
      return 'leftForce' in this.controlValues && 'rightForce' in this.controlValues;
    },

    get netForce() {
      return (this.controlValues.leftForce || 0) - (this.controlValues.rightForce || 0);
    },

    get netForceReadout() {
      if (this.netForce === 0) return 'Balanced! Net Force: 0 N';
      return `Net Force: ${Math.abs(this.netForce)} N → ${this.netForce > 0 ? 'Rival' : 'You'}`;
    },

    // ===== Asset resolution (on-demand: only called from templates for the active step) =====
    resolveAsset(id) {
      return this.lesson?.asset_manifest?.[id] || '';
    },

    // ===== Lifecycle =====
    async init() {
      // PREFETCH: pull the entire lesson module (content, evaluation, character
      // library, asset manifest) once, up front. Every subsequent slide/step
      // lookup runs off this in-memory object; only image bytes referenced by
      // the *active* step's <img>/<video> tags are fetched on demand.
      try {
        const res = await fetch('/api/lessons/load');
        this.lesson = await res.json();
        this.xp = this.lesson?.user_profile?.starting_xp ?? 0;
        this.selectedCharacterId = this.lesson?.character_library?.[0]?.id || null;
        this.initStep();
      } finally {
        this.loading = false;
        this.startTimer();
      }
    },

    initStep() {
      this.answered = false;
      this.attempts = 0;
      this.showHint = false;
      this.selectedOptionId = null;
      this.freeTextAnswer = '';
      this.freeTextWrong = false;
      this.dropdownAnswer = '';
      this.dropdownWrong = false;
      this.slideIndex = 0;
      this.storyIndex = 0;
      this.initControls();
      this.initObjects();
    },

    initControls() {
      const values = {};
      const controls = this.currentStep?.scene?.controls || [];
      controls.forEach((c) => {
        if (c.type !== 'button') values[c.id] = c.default ?? 0;
      });
      this.controlValues = values;
    },

    initObjects() {
      const positions = {};
      const objects = this.currentStep?.scene?.objects || [];
      objects.forEach((o) => {
        positions[o.id] = { ...o.default_pos };
      });
      this.objectPositions = positions;
    },

    startTimer() {
      clearInterval(this.timerHandle);
      this.elapsedSeconds = 0;
      this.timerHandle = setInterval(() => {
        this.elapsedSeconds++;
      }, 1000);
    },

    // ===== Scene object helpers =====
    getObjectPos(id) {
      return this.objectPositions[id] || { x: 50, y: 50 };
    },

    characterForObject(obj) {
      if (obj.character_source === 'selected_character') {
        return this.selectedCharacter || { kit_color: '#38bdf8', trim_color: '#1d4ed8' };
      }
      return obj.character_source;
    },

    arrowLenFor(obj) {
      if (!obj.arrow) return 0;
      const val = this.controlValues[obj.arrow.control_ref] || 0;
      const max = obj.arrow.max_control || 100;
      return 4 + (val / max) * 22;
    },

    arrowGeometry(obj) {
      if (!obj.arrow) return null;
      const charPos = this.getObjectPos(obj.id);
      const targetPos = this.getObjectPos(obj.arrow.toward);
      const dir = targetPos.x >= charPos.x ? 1 : -1;
      const startX = charPos.x + dir * 4;
      const len = this.arrowLenFor(obj);
      return { startX, endX: startX + dir * len, y: targetPos.y, dir };
    },

    handleZoneClick(obj) {
      this.zoneToast = obj.label;
      clearTimeout(this.zoneToastTimer);
      this.zoneToastTimer = setTimeout(() => (this.zoneToast = ''), 2000);
    },

    selectCharacter(c) {
      this.selectedCharacterId = c.id;
      const leftForceControl = this.currentStep?.scene?.controls?.find((ctrl) => ctrl.id === 'leftForce');
      if (leftForceControl) this.controlValues.leftForce = leftForceControl.default;
    },

    // ===== Whitelisted behavior interpreter =====
    // Only resolves numbers and known controlValues keys through +,-,*,/ and
    // comparison operators. No eval/Function — server-supplied "code" can only
    // ever be one of these fixed shapes, never arbitrary JS.
    resolveToken(tok) {
      tok = tok.trim();
      if (/^-?\d+(\.\d+)?$/.test(tok)) return parseFloat(tok);
      if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(tok)) return Number(this.controlValues[tok] ?? 0);
      return 0;
    },

    evalArithmetic(expr) {
      const m = String(expr).trim().match(/^(.+?)\s*([+\-*/])\s*(.+)$/);
      if (!m) return this.resolveToken(expr);
      const [, a, op, b] = m;
      const av = this.resolveToken(a);
      const bv = this.resolveToken(b);
      switch (op) {
        case '+': return av + bv;
        case '-': return av - bv;
        case '*': return av * bv;
        case '/': return bv !== 0 ? av / bv : 0;
        default: return 0;
      }
    },

    evalCondition(expr) {
      const m = String(expr).trim().match(/^(.+?)\s*(>=|<=|==|>|<)\s*(.+)$/);
      if (!m) return false;
      const [, lhs, op, rhs] = m;
      const lv = this.evalArithmetic(lhs);
      const rv = this.evalArithmetic(rhs);
      switch (op) {
        case '>=': return lv >= rv;
        case '<=': return lv <= rv;
        case '==': return lv === rv;
        case '>': return lv > rv;
        case '<': return lv < rv;
        default: return false;
      }
    },

    runAction(action) {
      const objects = this.currentStep?.scene?.objects || [];
      if (action.action === 'move') {
        const obj = objects.find((o) => o.id === action.target);
        const pos = this.objectPositions[action.target];
        if (!obj || !pos) return;
        const maxTravel = 25;
        const mag = this.evalArithmetic(action.magnitude_expr || '0');
        const travel = Math.max(0, Math.min(maxTravel, (mag / 100) * maxTravel));
        pos.x = action.toward === 'right' ? obj.default_pos.x + travel : obj.default_pos.x - travel;
      } else if (action.action === 'stop') {
        const obj = objects.find((o) => o.id === action.target);
        const pos = this.objectPositions[action.target];
        if (obj && pos) pos.x = obj.default_pos.x;
      } else if (action.action === 'show_toast') {
        this.zoneToast = action.text || '';
        clearTimeout(this.zoneToastTimer);
        this.zoneToastTimer = setTimeout(() => (this.zoneToast = ''), 2000);
      } else if (action.action === 'set_style') {
        // reserved for future declarative styling actions
      }
    },

    runBehaviors(triggerOn, controlId) {
      const behaviors = this.currentStep?.scene?.behaviors || [];
      behaviors.forEach((b) => {
        if (b.trigger?.on !== triggerOn || b.trigger?.control !== controlId) return;
        (b.rules || []).forEach((rule) => {
          if (this.evalCondition(rule.if)) {
            (rule.then || []).forEach((action) => this.runAction(action));
          }
        });
      });
    },

    onControlClick(control) {
      this.runBehaviors('click', control.id);
    },

    onControlChange(control) {
      this.runBehaviors('change', control.id);
    },

    // ===== Evaluation (3 fixed types, all funnel into the same XP/modal flow) =====
    handleCorrect() {
      this.answered = true;
      this.xp += 50;
      this.xpBumped = true;
      setTimeout(() => (this.xpBumped = false), 400);
      this.showCorrectModal = true;
    },

    selectOption(opt) {
      if (this.answered) return;
      this.attempts++;
      this.selectedOptionId = opt.id;
      if (opt.is_correct) this.handleCorrect();
    },

    submitFreeText() {
      if (this.answered) return;
      this.attempts++;
      const norm = (this.freeTextAnswer || '').trim().toLowerCase();
      const accepted = (this.currentStep?.evaluation?.accepted_answers || []).map((a) => a.trim().toLowerCase());
      if (accepted.includes(norm)) {
        this.freeTextWrong = false;
        this.handleCorrect();
      } else {
        this.freeTextWrong = true;
      }
    },

    submitDropdown() {
      if (this.answered) return;
      this.attempts++;
      if (this.dropdownAnswer === this.currentStep?.evaluation?.correct_choice) {
        this.dropdownWrong = false;
        this.handleCorrect();
      } else {
        this.dropdownWrong = true;
      }
    },

    // ===== Slideshow / story navigation =====
    nextSlide() {
      const total = this.currentStep?.slides?.length || 0;
      if (this.slideIndex + 1 < total) this.slideIndex++;
    },
    prevSlide() {
      if (this.slideIndex > 0) this.slideIndex--;
    },

    nextPanel() {
      const total = this.currentStep?.panels?.length || 0;
      if (this.storyIndex + 1 < total) this.storyIndex++;
    },

    // ===== Step / session navigation =====
    nextStep() {
      if (this.currentStepIndex + 1 < (this.lesson?.total_steps || 0)) {
        this.currentStepIndex++;
        this.initStep();
      } else {
        this.zoneToast = 'Lesson complete! 🎉';
        clearTimeout(this.zoneToastTimer);
        this.zoneToastTimer = setTimeout(() => (this.zoneToast = ''), 3000);
      }
    },

    toggleListening() {
      this.listening = !this.listening;
      if (this.listening) {
        setTimeout(() => (this.listening = false), 3000);
      }
    },

    abortAndRestart() {
      this.currentStepIndex = 0;
      this.xp = this.lesson?.user_profile?.starting_xp ?? 0;
      this.selectedCharacterId = this.lesson?.character_library?.[0]?.id || null;
      this.showCorrectModal = false;
      this.listening = false;
      this.initStep();
      this.startTimer();
    },

    // ===== Generate-a-custom-lesson request flow =====
    openRequestForm() {
      this.stopPolling();
      this.requestStatus = null;
      this.requestError = '';
      this.view = 'request';
    },

    closeRequestForm() {
      this.stopPolling();
      this.view = 'canvas';
    },

    stopPolling() {
      clearInterval(this.requestPollHandle);
      this.requestPollHandle = null;
    },

    async submitLessonRequest() {
      this.requestError = '';
      this.requestStatus = 'pending';
      try {
        const studentRes = await fetch('/api/students', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: this.requestForm.name || 'Guest',
            age: this.requestForm.age ? Number(this.requestForm.age) : null,
            grade: this.requestForm.grade || null,
            favorite_sport: this.requestForm.favorite_sport || null,
          }),
        });
        if (!studentRes.ok) throw new Error('failed to register student');
        const student = await studentRes.json();

        const reqRes = await fetch('/api/lesson-requests', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            student_id: student.id,
            skill: this.requestForm.skill,
            modality: this.requestForm.modality,
          }),
        });
        if (!reqRes.ok) throw new Error('failed to create lesson request');
        const reqData = await reqRes.json();

        this.pollLessonRequest(reqData.id);
      } catch (err) {
        this.requestStatus = 'failed';
        this.requestError = 'Could not reach the server — is it running?';
      }
    },

    pollLessonRequest(requestId) {
      this.stopPolling();
      this.requestPollHandle = setInterval(async () => {
        let data;
        try {
          const res = await fetch(`/api/lesson-requests/${requestId}`);
          data = await res.json();
        } catch (err) {
          return; // transient network hiccup — keep polling
        }

        this.requestStatus = data.status;

        if (data.status === 'ready') {
          this.stopPolling();
          this.lesson = data.lesson;
          this.xp = this.lesson?.user_profile?.starting_xp ?? this.xp;
          this.selectedCharacterId = this.lesson?.character_library?.[0]?.id || null;
          this.currentStepIndex = 0;
          this.initStep();
          this.startTimer();
          this.view = 'canvas';
        } else if (data.status === 'failed') {
          this.stopPolling();
          this.requestError = data.failure_reason || 'Generation failed.';
        }
      }, 2000);
    },
  };
}
