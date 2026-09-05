import { useState } from "react";
import type { AttachmentPreview } from "../types";
export function useContractAttachmentPreview() {
    const [attachmentPreview, setAttachmentPreview] = useState<AttachmentPreview | null>(null);
    const closeAttachmentPreview = () => {
        if (attachmentPreview?.url)
            URL.revokeObjectURL(attachmentPreview.url);
        setAttachmentPreview(null);
    };
    return { attachmentPreview, setAttachmentPreview, closeAttachmentPreview };
}
