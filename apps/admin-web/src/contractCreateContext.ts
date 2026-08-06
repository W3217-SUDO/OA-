import dayjs, { type Dayjs } from "dayjs";

export type LinkedCustomerContext = {
  id: number;
  name: string;
  serial_no?: string;
  at?: number;
};

type ContextStorage = Pick<Storage, "getItem" | "removeItem">;
const CUSTOMER_CONTEXT_KEY = "sunhold:contract-customer";
export const CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY = "sunhold:contract-customer-route-source";
const MAX_CONTEXT_AGE_MS = 60 * 60 * 1000;

export const createContractNumber = (value: Dayjs = dayjs()): string => {
  const sequenceSeed = value.month() * 31 + value.date();
  const compactSequence = 10000 + sequenceSeed;
  return `SHHT${value.format("YY")}${compactSequence.toString().padStart(5, "0")}`;
};

export const createContractCustomerContextConsumer = (
  storage: ContextStorage,
  now: () => number = Date.now,
) => {
  let initialized = false;
  let cached: LinkedCustomerContext | null = null;

  return {
    consume: (): LinkedCustomerContext | null => {
      if (initialized) return cached;
      initialized = true;
      try {
        const context = JSON.parse(storage.getItem(CUSTOMER_CONTEXT_KEY) || "null");
        storage.removeItem(CUSTOMER_CONTEXT_KEY);
        if (!context?.id || !context?.name) return null;
        if (context.at && now() - Number(context.at) > MAX_CONTEXT_AGE_MS) return null;
        cached = {
          id: Number(context.id),
          name: String(context.name),
          serial_no: context.serial_no ? String(context.serial_no) : "",
          at: Number(context.at || 0),
        };
        return cached;
      } catch {
        storage.removeItem(CUSTOMER_CONTEXT_KEY);
        return null;
      }
    },
    reset: () => {
      initialized = false;
      cached = null;
    },
  };
};

export const clearContractCustomerContext = (storage: ContextStorage) => {
  storage.removeItem(CUSTOMER_CONTEXT_KEY);
};
