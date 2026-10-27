import { RobotOutlined, SafetyCertificateOutlined, SolutionOutlined, UserOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import type { ReactNode } from "react";
import FeedbackAttachments from "./FeedbackAttachments";
import FeedbackEventImage from "./FeedbackEventImage";
import { feedbackEventHasMessage, feedbackSpeaker, feedbackSpeakerName, feedbackStatusText, isFeedbackStatusEvent, type FeedbackSpeaker } from "./chat";
import type { FeedbackEvent } from "./types";

const AVATAR_ICONS: Record<FeedbackSpeaker, ReactNode> = {
  reporter: <UserOutlined />, admin: <SafetyCertificateOutlined />, bot: <RobotOutlined />, assignee: <SolutionOutlined />,
};

// 处理记录里的一条：状态变化是居中小灰条；回复（以及状态变化附带的说明、截图）是气泡，提交人在右、处理方在左。
export default function FeedbackChatEntry({ feedbackId, event }: { feedbackId: number; event: FeedbackEvent }) {
  const speaker = feedbackSpeaker(event);
  const time = dayjs(event.created_at).format("MM-DD HH:mm");
  return <>
    {isFeedbackStatusEvent(event) && <div className="feedback-chat-status" role="note">
      <span>{feedbackStatusText(event)}</span>
      <span className="feedback-chat-status-time">{time}</span>
    </div>}
    {feedbackEventHasMessage(event) && <div className={`feedback-chat-row is-${speaker}`}>
      <span className={`feedback-chat-avatar is-${speaker}`} aria-hidden="true">{AVATAR_ICONS[speaker]}</span>
      <div className="feedback-chat-body">
        <div className="feedback-chat-meta">
          <span className="feedback-chat-name">{feedbackSpeakerName(event)}</span>
          <span>{time}</span>
        </div>
        <div className="feedback-chat-bubble">
          {event.comment && <div className="feedback-chat-text">{event.comment}</div>}
          {event.attachments?.length
            ? <FeedbackAttachments feedbackId={feedbackId} attachments={event.attachments} compact />
            : event.has_screenshot && <FeedbackEventImage feedbackId={feedbackId} eventId={event.id} />}
        </div>
      </div>
    </div>}
  </>;
}
