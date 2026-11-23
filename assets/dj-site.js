(() => {
    const languageSelect = document.querySelector("#site-language");
    const defaultLanguage = languageSelect.options[0].value;
    const supportedLanguages = new Set(Array.from(languageSelect.options, (option) => option.value));
    const preferenceKey = "djmag-language";

    const initialUrl = new URL(window.location.href);
    const requestedLanguage = initialUrl.searchParams.get("lang");
    let savedLanguage;
    try {
        savedLanguage = localStorage.getItem(preferenceKey);
    } catch {
        // URLs still carry the preference when browser storage is unavailable.
    }

    const translatedText = Array.from(document.querySelectorAll("[data-zh]"), (element) => ({
        element,
        original: element.textContent,
    }));
    const translatedAttributes = [
        ["placeholder", "data-zh-placeholder"],
        ["alt", "data-zh-alt"],
    ].flatMap(([attribute, translation]) =>
        Array.from(document.querySelectorAll(`[${translation}]`), (element) => ({
            element,
            attribute,
            original: element.getAttribute(attribute),
            chinese: element.getAttribute(translation),
        })),
    );
    const navigationLinks = document.querySelectorAll("[data-dj-link]");
    const biographies = Array.from(document.querySelectorAll("[data-bio-language]"));

    function linkInLanguage(link, language) {
        const url = new URL(link);
        url.searchParams.set("lang", language);
        return url;
    }

    function applyLanguage(language) {
        const inChinese = language === "zh-CN";
        document.documentElement.lang = language;
        languageSelect.value = language;
        for (const { element, original } of translatedText) {
            element.textContent = inChinese ? element.dataset.zh : original;
        }
        for (const { element, attribute, original, chinese } of translatedAttributes) {
            element.setAttribute(attribute, inChinese ? chinese : original);
        }
        const biographyLanguage = biographies.some((element) => element.dataset.bioLanguage === language)
            ? language : defaultLanguage;
        for (const element of biographies) {
            element.hidden = element.dataset.bioLanguage !== biographyLanguage;
        }
        for (const link of navigationLinks) {
            link.href = linkInLanguage(link.href, language);
        }
        try {
            localStorage.setItem(preferenceKey, language);
        } catch {
            // The page and its links still use the selected language.
        }
    }

    languageSelect.addEventListener("change", () => {
        const language = languageSelect.value;
        const url = linkInLanguage(window.location.href, language);
        window.history.replaceState(window.history.state, "", url);
        applyLanguage(language);
    });
    const initialLanguage = [requestedLanguage, savedLanguage].find((language) => supportedLanguages.has(language));
    applyLanguage(initialLanguage ?? defaultLanguage);

    const search = document.querySelector("#search");
    if (!search) return;

    const normalize = (value) => value.normalize("NFKC").trim().toLowerCase();
    const cards = Array.from(document.querySelectorAll(".card[data-search]"), (element) => ({
        element,
        names: JSON.parse(element.dataset.search).map(normalize),
    }));
    const emptyMessage = document.querySelector("[data-no-results]");

    function filterArtists() {
        const query = normalize(search.value);
        let foundMatch = false;
        for (const { element, names } of cards) {
            const matches = !query || names.some((name) => name.includes(query));
            element.hidden = !matches;
            foundMatch ||= matches;
        }
        emptyMessage.hidden = !query || foundMatch;
    }

    search.addEventListener("input", filterArtists);
    filterArtists();
})();
