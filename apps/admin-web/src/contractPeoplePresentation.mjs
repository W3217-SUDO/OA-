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

export const displayChinesePersonName = (value, directory = []) => {
  const raw = normalize(value);
  const candidate = directoryName(raw, directory);
  if (isChinesePersonName(raw)) return raw;
  // A non-empty system display_name is authoritative, regardless of language or
  // whether it is identical to the login account.
  return candidate || PERSON_NAME_PLACEHOLDER;
};

export const displayChinesePersonNames = (values, directory = []) => {
  const source = Array.isArray(values) ? values : String(values || "").split(/[、,，;；]/);
  const names = source.map((value) => displayChinesePersonName(value, directory));
  return names.length ? names.join("、") : PERSON_NAME_PLACEHOLDER;
};

export const buildChinesePersonOptions = (users = [], predicate = () => true, _options = {}) => {
  const candidates = users
    .filter((user) => predicate(user))
    .map((user) => ({ username: normalize(user?.username), display_name: displayLabel(user?.display_name) }))
    .filter((user) => {
      if (!user.username || !user.display_name || user.display_name === PERSON_NAME_PLACEHOLDER) return false;
      return true;
    });
  const counts = candidates.reduce((result, user) => {
    result.set(user.display_name, (result.get(user.display_name) || 0) + 1);
    return result;
  }, new Map());
  return candidates
    .filter((user) => counts.get(user.display_name) === 1)
    .map((user) => ({ value: user.username, label: user.display_name }));
};
