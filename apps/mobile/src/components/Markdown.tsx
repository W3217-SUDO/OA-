import { StyleSheet, Text, View } from "react-native";
import { colors } from "@/lib/theme";

// 智能体回复是 Markdown。这里只渲染常见结构（标题、列表、引用、代码块、粗体、行内代码），
// 表格等复杂结构按原文显示，内容不丢。

function inline(text: string, keyPrefix: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) return <Text key={`${keyPrefix}-${index}`} style={styles.bold}>{part.slice(2, -2)}</Text>;
    if (part.startsWith("`") && part.endsWith("`")) return <Text key={`${keyPrefix}-${index}`} style={styles.code}>{part.slice(1, -1)}</Text>;
    return part;
  });
}

export function Markdown({ content, color = colors.text }: { content: string; color?: string }) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: React.ReactNode[] = [];
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (line.trim().startsWith("```")) {
      const code: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith("```")) code.push(lines[i++]);
      blocks.push(<Text key={i} style={styles.codeBlock} selectable>{code.join("\n")}</Text>);
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      blocks.push(<Text key={i} style={[styles.heading, { color, fontSize: heading[1].length <= 2 ? 17 : 15 }]}>{inline(heading[2], String(i))}</Text>);
      continue;
    }
    const bullet = line.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
    if (bullet) {
      const marker = /\d/.test(bullet[2]) ? bullet[2] : "•";
      blocks.push(
        <View key={i} style={[styles.bulletRow, { paddingLeft: Math.min(bullet[1].length, 6) * 6 }]}>
          <Text style={[styles.text, { color }]}>{marker} </Text>
          <Text style={[styles.text, styles.flex, { color }]} selectable>{inline(bullet[3], String(i))}</Text>
        </View>,
      );
      continue;
    }
    if (line.startsWith(">")) {
      blocks.push(<Text key={i} style={[styles.quote]} selectable>{inline(line.replace(/^>\s?/, ""), String(i))}</Text>);
      continue;
    }
    if (!line.trim()) {
      blocks.push(<View key={i} style={{ height: 6 }} />);
      continue;
    }
    blocks.push(<Text key={i} style={[styles.text, { color }]} selectable>{inline(line, String(i))}</Text>);
  }
  return <View>{blocks}</View>;
}

const styles = StyleSheet.create({
  text: { fontSize: 15, lineHeight: 22 },
  flex: { flex: 1 },
  bold: { fontWeight: "700" },
  code: { fontFamily: "monospace", backgroundColor: "#eef1f0", fontSize: 13 },
  codeBlock: { fontFamily: "monospace", fontSize: 13, backgroundColor: "#eef1f0", padding: 8, borderRadius: 6, marginVertical: 4, color: colors.text },
  heading: { fontWeight: "700", marginTop: 6, marginBottom: 2 },
  bulletRow: { flexDirection: "row" },
  quote: { borderLeftWidth: 3, borderColor: colors.border, paddingLeft: 8, color: colors.textSecondary, fontSize: 14, lineHeight: 21 },
});
