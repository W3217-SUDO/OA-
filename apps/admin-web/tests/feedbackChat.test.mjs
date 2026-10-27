// 问题处理记录聊天框（2026-10-27）：谁在说话、靠哪边、哪些是居中状态条。
import assert from "node:assert/strict";
import test from "node:test";
import { feedbackEventHasMessage, feedbackSpeaker, feedbackSpeakerName, feedbackStatusText, isFeedbackStatusEvent } from "../src/feedback/chat.ts";

const base = { id: 1, from_status: "待处理", to_status: "待处理", comment: "", created_at: "", has_screenshot: false, attachments: [] };

test("问题处理助手和管理者分开显示", () => {
  const bot = { ...base, action: "回复", operator: "feedback-bot", operator_display_name: "问题处理助手", operator_role: "bot" };
  const admin = { ...base, action: "回复", operator: "admin", operator_display_name: "管理者", operator_role: "admin" };
  assert.equal(feedbackSpeaker(bot), "bot");
  assert.equal(feedbackSpeakerName(bot), "问题处理助手");
  assert.equal(feedbackSpeakerName({ ...bot, operator_display_name: "" }), "问题处理助手");
  assert.equal(feedbackSpeaker(admin), "admin");
  assert.equal(feedbackSpeakerName(admin), "管理者");
  // 老接口没有 operator_role 时按处理方（管理者）显示。
  assert.equal(feedbackSpeaker({ operator_role: undefined }), "admin");
});

test("状态变化居中，带说明时再出一个气泡", () => {
  const done = { ...base, action: "处理完成，请验证", to_status: "待验证", operator: "feedback-bot", operator_display_name: "问题处理助手", operator_role: "bot" };
  assert.equal(isFeedbackStatusEvent(done), true);
  assert.equal(feedbackStatusText(done), "问题处理助手 处理完成，请验证 → 待验证");
  assert.equal(feedbackEventHasMessage(done), false);
  assert.equal(feedbackEventHasMessage({ ...done, comment: "已在 1.2.1 修复" }), true);
  const submit = { ...base, action: "提交反馈", from_status: "", operator: "gaoqinlan", operator_display_name: "高勤兰", operator_role: "reporter" };
  assert.equal(feedbackStatusText(submit), "高勤兰 提交了反馈 → 待处理");
  const confirm = { ...base, action: "确认修改", operator: "gaoqinlan", operator_display_name: "高勤兰", operator_role: "reporter" };
  assert.equal(feedbackStatusText(confirm), "高勤兰 确认修改");
  const reply = { ...base, action: "回复", comment: "还是两行", operator: "gaoqinlan", operator_display_name: "高勤兰", operator_role: "reporter" };
  assert.equal(isFeedbackStatusEvent(reply), false);
  assert.equal(feedbackEventHasMessage(reply), true);
  assert.equal(feedbackSpeaker(reply), "reporter");
  const assign = { ...base, action: "指派处理人", comment: "未指派 → 陶国南（tgn）", operator: "admin", operator_display_name: "管理者", operator_role: "admin" };
  assert.equal(feedbackStatusText(assign), "管理者 指派处理人：未指派 → 陶国南（tgn）");
  assert.equal(feedbackEventHasMessage(assign), false);
});
