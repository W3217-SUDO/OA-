// SDK 的持久事件与实时增量分别传输，前端继续使用原有 SSE 协议。
export const name = 'oa-stream';
export const inject = ['agents', 'tools'];

export function apply(ctx, config) {
  ctx.on('agent/created', ({agent}) => {
    // 普通 OA 工作区只开放已授权的技能与 MCP，不继承编码工具或自动派生子代理。
    // 外部插件由管理员安装并随 profile 加载；宿主编码工具已在 OA 配置层停用。
    if (!config.nativePlugins) agent.ctx.tools.restrict({allow: config.allowedTools});
  });
  ctx.on('agent/assistant-stream', ({agent, frame}) => {
    if (frame.type !== 'chunk' || frame.chunk.type !== 'text-delta') return;
    process.stdout.write(JSON.stringify({jsonrpc: '2.0', method: 'oa.assistant.delta',
      params: {sessionId: agent.session.id, text: frame.chunk.text}}) + '\n');
  });
}
