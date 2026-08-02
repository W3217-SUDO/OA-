type StorageLike = Pick<Storage, "getItem" | "setItem">;

const storageKey = (view: string) => `sunhold:contract-query:${String(view || "contract-mine").trim()}`;

export const readContractListQuery = (
  storage: StorageLike,
  view: string,
): Record<string, unknown> => {
  try {
    const parsed = JSON.parse(storage.getItem(storageKey(view)) || "{}");
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
};

export const saveContractListQuery = (
  storage: StorageLike,
  view: string,
  query: Record<string, unknown>,
) => {
  storage.setItem(storageKey(view), JSON.stringify(query));
};
