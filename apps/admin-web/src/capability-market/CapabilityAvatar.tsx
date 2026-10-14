import { useEffect, useState } from "react";
import { Tooltip } from "antd";
import { RobotOutlined, WarningOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "../personal-agent/types";

export function CapabilityAvatar({ source, authenticated = false }: { source: string; authenticated?: boolean }) {
  const [image, setImage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!source || !authenticated) return;
    const controller = new AbortController();
    let objectUrl = "";
    setImage(""); setError("");
    void api.get<Blob>(source, { responseType: "blob", signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) { objectUrl = URL.createObjectURL(data); setImage(objectUrl); } })
      .catch(failure => { if (!controller.signal.aborted) setError(errorText(failure, "头像加载失败")); });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [source, authenticated]);
  const src = authenticated ? image : source;
  if (error) return <Tooltip title={error}><span className="capability-market-icon" aria-label="头像加载失败"><WarningOutlined /></span></Tooltip>;
  return src ? <img src={src} alt="" width={44} height={44} /> : <span className="capability-market-icon"><RobotOutlined /></span>;
}
