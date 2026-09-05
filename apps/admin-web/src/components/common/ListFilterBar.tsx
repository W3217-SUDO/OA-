import { Form,type FormProps } from "antd";
import type { ReactNode } from "react";

/** Shared filter form layout. The caller owns query state, fields and button policy. */
export function ListFilterBar<Values = Record<string, unknown>>({ actions, children, ...props }: Omit<FormProps<Values>, "children"> & { children?: ReactNode; actions?: ReactNode }) {
  return <Form<Values> {...props}>{children}{actions && <Form.Item>{actions}</Form.Item>}</Form>;
}
