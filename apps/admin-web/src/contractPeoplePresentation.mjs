export const PERSON_NAME_PLACEHOLDER = "姓名待维护";

const PERSON_NAME_PATTERN = /[\u3400-\u9fff]/;

const normalize = (value) => String(value || "").normalize("NFKC").trim().replace(/\s+/g, "");
const displayLabel = (value) => String(value || "").normalize("NFKC").trim().replace(/\s+/g, " ");

export const isChinesePersonName = (value) => {
  const name = normalize(value);
  return Boolean(name) && PERSON_NAME_PATTERN.test(name);
};

const directoryName = (value, directory) => {
  const identifier = normalize(value);
  const matched = directory.find((user) =>
    normalize(user?.username) === identifier || normalize(user?.display_name) === identifier,
  );
  return displayLabel(matched?.display_name);
};

const isDirectoryPersonName = (value, directory) => {
  const identifier = normalize(value);
  return directory.some((user) =>
    (normalize(user?.username) === identifier || normalize(user?.display_name) === identifier) &&
    normalize(user?.display_name) !== normalize(user?.username),
  );
};

export const displayChinesePersonName = (value, directory = []) => {
  const raw = normalize(value);
  const candidate = directoryName(raw, directory);
  if (isChinesePersonName(raw)) return raw;
  if (isChinesePersonName(candidate)) return candidate;
  // English names are valid only when the directory identifies them as an employee's name.
  return isDirectoryPersonName(raw, directory) ? candidate : PERSON_NAME_PLACEHOLDER;
};

export const displayChinesePersonNames = (values, directory = []) => {
  const source = Array.isArray(values) ? values : String(values || "").split(/[、,，;；]/);
  const names = source.map((value) => displayChinesePersonName(value, directory));
  return names.length ? names.join("、") : PERSON_NAME_PLACEHOLDER;
};

export const buildChinesePersonOptions = (users = [], predicate = () => true, { allowNonChinese = true } = {}) => {
  const candidates = users
    .filter((user) => predicate(user))
    .map((user) => ({ username: normalize(user?.username), display_name: displayLabel(user?.display_name) }))
    .filter((user) => {
      if (!user.username || !user.display_name || user.display_name === PERSON_NAME_PLACEHOLDER) return false;
      if (isChinesePersonName(user.display_name)) return true;
      // A non-Chinese name is valid when HR stores it separately from the login account.
      return allowNonChinese && normalize(user.display_name) !== user.username;
    });
  const counts = candidates.reduce((result, user) => {
    result.set(user.display_name, (result.get(user.display_name) || 0) + 1);
    return result;
  }, new Map());
  return candidates
    .filter((user) => counts.get(user.display_name) === 1)
    .map((user) => ({ value: user.username, label: user.display_name }));
};
