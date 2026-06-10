package com.yupi.aicodehelper.ai.workflow;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Node 1: PII 过滤 + 意图分类
 * Routes: knowledge_query | casual_chat | memory_query
 */
@Slf4j
@Component
public class IntentClassifier {

    // PII patterns
    private static final Pattern EMAIL_PATTERN = Pattern.compile(
            "[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+");
    private static final Pattern PHONE_PATTERN = Pattern.compile("1[3-9]\\d{9}");
    private static final Pattern ID_CARD_PATTERN = Pattern.compile("\\b\\d{17}[\\dXx]\\b");
    private static final Pattern IP_PATTERN = Pattern.compile(
            "\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b");

    // Intent keywords
    private static final Set<String> CASUAL_KW = Set.of(
            "你好", "谢谢", "再见", "嗨", "hello", "hi", "bye");
    private static final Set<String> MEMORY_KW = Set.of(
            "记住", "偏好", "记忆", "永久", "总是", "以后", "不需要",
            "禁用", "启用", "别记", "忘记", "别用", "以后都", "不要记录", "别记下", "忘掉");

    public static class PiiHit {
        String type;
        String matched;

        PiiHit(String type, String matched) {
            this.type = type;
            this.matched = matched;
        }
    }

    public WorkflowState classify(WorkflowState state) {
        String query = state.getString("query");
        List<PiiHit> detections = new ArrayList<>();
        String clean = query;

        // Detect and remove PII
        if (EMAIL_PATTERN.matcher(clean).find()) {
            var m = EMAIL_PATTERN.matcher(clean);
            while (m.find()) {
                detections.add(new PiiHit("email", m.group()));
            }
            clean = EMAIL_PATTERN.matcher(clean).replaceAll("[EMAIL]");
        }
        if (PHONE_PATTERN.matcher(clean).find()) {
            var m = PHONE_PATTERN.matcher(clean);
            while (m.find()) {
                detections.add(new PiiHit("phone", m.group()));
            }
            clean = PHONE_PATTERN.matcher(clean).replaceAll("[PHONE]");
        }
        if (ID_CARD_PATTERN.matcher(clean).find()) {
            var m = ID_CARD_PATTERN.matcher(clean);
            while (m.find()) {
                detections.add(new PiiHit("id_card", m.group()));
            }
            clean = ID_CARD_PATTERN.matcher(clean).replaceAll("[ID_CARD]");
        }
        if (IP_PATTERN.matcher(clean).find()) {
            var m = IP_PATTERN.matcher(clean);
            while (m.find()) {
                detections.add(new PiiHit("ip_address", m.group()));
            }
            clean = IP_PATTERN.matcher(clean).replaceAll("[IP]");
        }

        state.set("clean_query", clean);
        state.set("pii_detections", detections);
        state.set("has_pii", !detections.isEmpty());

        if (!detections.isEmpty()) {
            log.info("[classify] PII detected: {} patterns", detections.size());
        }

        // Intent classification: memory first, then casual, default to knowledge
        for (String kw : MEMORY_KW) {
            if (clean.contains(kw)) {
                state.set("intent", "memory_query");
                log.info("[classify] → memory_query");
                return state;
            }
        }

        String trimmed = clean.trim();
        for (String ck : CASUAL_KW) {
            if (trimmed.equals(ck) || (trimmed.length() <= 3 && trimmed.equalsIgnoreCase(ck))) {
                state.set("intent", "casual_chat");
                log.info("[classify] → casual_chat");
                return state;
            }
        }

        state.set("intent", "knowledge_query");
        log.info("[classify] → knowledge_query");
        return state;
    }
}
