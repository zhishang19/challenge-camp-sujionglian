package com.yupi.aicodehelper.ai.workflow;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Node 3: Format output based on intent type.
 */
@Slf4j
@Component
public class OutputFormatter {

    public WorkflowState format(WorkflowState state) {
        String intent = state.getString("intent");
        StringBuilder sb = new StringBuilder();

        // PII info
        if (Boolean.TRUE.equals(state.get("has_pii"))) {
            @SuppressWarnings("unchecked")
            List<IntentClassifier.PiiHit> detections = state.get("pii_detections");
            int piiCount = detections != null ? detections.size() : 0;
            sb.append("[PII] Filtered: ").append(piiCount).append(" pattern(s) redacted\n");
        }

        switch (intent) {
            case "knowledge_query" -> {
                @SuppressWarnings("unchecked")
                List<KnowledgeRetriever.KnowledgeHit> retrieved = state.get("retrieved");
                if (retrieved != null && !retrieved.isEmpty()) {
                    sb.append("=== 知识检索结果 ===\n");
                    for (var hit : retrieved) {
                        sb.append(String.format("[%s] score=%.4f | %s\n",
                                hit.item.id, hit.score,
                                hit.item.bodyText.length() > 100
                                        ? hit.item.bodyText.substring(0, 100) + "..."
                                        : hit.item.bodyText));
                    }
                } else {
                    sb.append("未找到相关知识条目。");
                }
            }
            case "casual_chat" -> sb.append(state.getString("chat_reply"));
            case "memory_query" -> sb.append(state.getString("memory_response"));
            default -> sb.append("无法处理该请求。");
        }

        state.set("final_output", sb.toString().trim());
        log.info("[output] intent={}, length={}", intent, sb.length());
        return state;
    }
}
