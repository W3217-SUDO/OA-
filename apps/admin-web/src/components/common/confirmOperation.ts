import type { ModalFuncProps } from "antd";
import { Modal } from "antd";

export type ConfirmOperationOptions = Omit<ModalFuncProps, "onOk"> & {
  onConfirm: NonNullable<ModalFuncProps["onOk"]>;
};

/** Keep the operation's promise attached to the dialog: rejection leaves it open. */
export function confirmOperation({ onConfirm, ...options }: ConfirmOperationOptions) {
  return Modal.confirm({ ...options, onOk: onConfirm });
}
