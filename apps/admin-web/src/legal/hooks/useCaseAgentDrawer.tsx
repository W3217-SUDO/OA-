import { useState, type PointerEvent as ReactPointerEvent } from "react";
export function useCaseAgentDrawer() {
    const [agentDrawerWidth, setAgentDrawerWidth] = useState(() => Math.min(720, Math.max(520, window.innerWidth * 0.46)));
    const startAgentDrawerResize = (event: ReactPointerEvent<HTMLDivElement>) => {
        event.preventDefault();
        const startX = event.clientX;
        const startWidth = agentDrawerWidth;
        const onMove = (moveEvent: PointerEvent) => setAgentDrawerWidth(Math.min(window.innerWidth * 0.92, Math.max(420, startWidth + startX - moveEvent.clientX)));
        const onUp = () => {
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onUp);
        };
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
    };
    return { agentDrawerWidth, setAgentDrawerWidth, startAgentDrawerResize };
}
