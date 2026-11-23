function ageFromBirthDate(value, today) {
    const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!parts) return null;

    const [, year, month, day] = parts.map(Number);
    const birthDate = new Date(0);
    birthDate.setUTCFullYear(year, month - 1, day);
    if (
        year === 0 ||
        birthDate.getUTCFullYear() !== year ||
        birthDate.getUTCMonth() + 1 !== month ||
        birthDate.getUTCDate() !== day
    ) return null;

    const currentMonth = today.getMonth() + 1;
    const birthdayPassed = currentMonth > month || (currentMonth === month && today.getDate() >= day);
    const age = today.getFullYear() - year - Number(!birthdayPassed);
    return age >= 0 ? age : null;
}

const ageOutput = document.querySelector("[data-birth-date]");
if (ageOutput) {
    const age = ageFromBirthDate(ageOutput.dataset.birthDate, new Date());
    if (age !== null) {
        ageOutput.textContent = age;
        ageOutput.previousElementSibling.hidden = false;
        ageOutput.hidden = false;
    }
}
