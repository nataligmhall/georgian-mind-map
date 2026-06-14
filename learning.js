(function () {
  const STORAGE_KEY = "georgian-mind-map-learning-v1";

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return { flagged: [], known: [] };
      const data = JSON.parse(raw);
      return {
        flagged: Array.isArray(data.flagged) ? data.flagged : [],
        known: Array.isArray(data.known) ? data.known : [],
      };
    } catch {
      return { flagged: [], known: [] };
    }
  }

  function save(data) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }

  function wordKey(themeId, ka) {
    return `${themeId}:${ka}`;
  }

  function parseKey(key) {
    const i = key.indexOf(":");
    return { themeId: key.slice(0, i), ka: key.slice(i + 1) };
  }

  function toggleIn(list, key) {
    const set = new Set(list);
    if (set.has(key)) set.delete(key);
    else set.add(key);
    return [...set];
  }

  window.LearningStore = {
    wordKey,
    parseKey,

    isFlagged(themeId, ka) {
      return load().flagged.includes(wordKey(themeId, ka));
    },

    isKnown(themeId, ka) {
      return load().known.includes(wordKey(themeId, ka));
    },

    toggleFlag(themeId, ka) {
      const data = load();
      data.flagged = toggleIn(data.flagged, wordKey(themeId, ka));
      save(data);
      return data.flagged.includes(wordKey(themeId, ka));
    },

    toggleKnown(themeId, ka) {
      const data = load();
      const key = wordKey(themeId, ka);
      data.known = toggleIn(data.known, key);
      if (data.known.includes(key)) {
        data.flagged = data.flagged.filter((k) => k !== key);
      }
      save(data);
      return data.known.includes(key);
    },

    unflag(themeId, ka) {
      const data = load();
      const key = wordKey(themeId, ka);
      data.flagged = data.flagged.filter((k) => k !== key);
      save(data);
    },

    getCounts() {
      const data = load();
      return { flagged: data.flagged.length, known: data.known.length };
    },

    getThemeProgress(themeId, totalWords) {
      if (!totalWords) return 0;
      const data = load();
      const prefix = `${themeId}:`;
      const known = data.known.filter((k) => k.startsWith(prefix)).length;
      return known / totalWords;
    },

    getFlaggedWords(dictionaryData) {
      const data = load();
      const lookup = new Map();
      dictionaryData.categories.forEach((cat) => {
        cat.words.forEach((w) => {
          lookup.set(wordKey(cat.id, w.ka), { ...w, themeId: cat.id, themeName: cat.name, page: cat.page });
        });
      });
      return data.flagged
        .map((key) => lookup.get(key))
        .filter(Boolean);
    },
  };
})();
