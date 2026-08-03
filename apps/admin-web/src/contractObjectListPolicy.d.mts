export declare const CONTRACT_OBJECT_DEFAULT_PAGE_SIZE: 10;
export declare const CONTRACT_OBJECT_PAGE_SIZES: readonly [10, 15, 20, 50, 100, 200];
export declare const sortContractObjectRows: <T extends object>(rows?: T[]) => T[];
export declare const sortContractRecordRows: <T extends object>(rows?: T[]) => T[];
export declare const paginateContractObjectRows: <T extends object>(rows?: T[], current?: number, pageSize?: number) => { items: T[]; current: number; pageSize: number; total: number };
