export type LegacyCaseDocumentGenerationItem = readonly [key: string, label: string];

export const LEGACY_CASE_DOCUMENT_GENERATION_ITEMS: readonly LegacyCaseDocumentGenerationItem[];

export function getLegacyCaseDocumentGenerationItems(): readonly LegacyCaseDocumentGenerationItem[];

export function dispatchCaseDocumentGenerationMenuClick(
  event: {
    key?: string | number;
    domEvent?: {
      preventDefault?: () => void;
      stopPropagation?: () => void;
    };
  },
  runAction: (key: string) => void,
): boolean;
