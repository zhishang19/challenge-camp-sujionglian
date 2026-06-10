package com.yupi.aicodehelper.ai.workflow;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.File;
import java.util.List;
import java.util.Map;

/**
 * LangGraph 3-Node Workflow orchestrator.
 *
 * Architecture: [classify] → [retrieve/chat/memory] → [output]
 * Knowledge source: phase2-consolidate/knowledge_items.json (D4 cleaned results)
 */
@Slf4j
@Service
public class WorkflowService {

    private final IntentClassifier classifier;
    private final KnowledgeRetriever knowledgeRetriever;
    private final ChatResponder chatResponder;
    private final OutputFormatter outputFormatter;
    private final SimpleStateGraph workflow;
    private final ObjectMapper objectMapper = new ObjectMapper();

    /** Path to D4 cleaned knowledge data */
    private static final String KNOWLEDGE_PATH =
            "../../phase2-consolidate/knowledge_items.json";

    public WorkflowService(IntentClassifier classifier,
                           KnowledgeRetriever knowledgeRetriever,
                           ChatResponder chatResponder,
                           OutputFormatter outputFormatter) {
        this.classifier = classifier;
        this.knowledgeRetriever = knowledgeRetriever;
        this.chatResponder = chatResponder;
        this.outputFormatter = outputFormatter;

        // Build the 3-node workflow
        this.workflow = new SimpleStateGraph()
                .addNode("classify", classifier::classify)
                .addNode("retrieve", knowledgeRetriever::retrieve)
                .addNode("chat", chatResponder::respond)
                .addNode("memory", this::handleMemory)
                .addNode("output", outputFormatter::format)
                .setEntryPoint("classify")
                .addConditionalEdges("classify",
                        s -> s.getString("intent"),
                        Map.of("knowledge_query", "retrieve",
                                "casual_chat", "chat",
                                "memory_query", "memory"))
                .addEdge("retrieve", "output")
                .addEdge("chat", "output")
                .addEdge("memory", "output")
                .setFinishPoint("output");
    }

    @PostConstruct
    public void init() {
        try {
            File file = new File(KNOWLEDGE_PATH);
            if (file.exists()) {
                List<Map<String, Object>> items = objectMapper.readValue(
                        file, new TypeReference<>() {});
                knowledgeRetriever.loadKnowledge(items);
                log.info("Workflow initialized with {} knowledge items from {}",
                        items.size(), KNOWLEDGE_PATH);
            } else {
                log.warn("Knowledge file not found: {}", file.getAbsolutePath());
            }
        } catch (Exception e) {
            log.warn("Failed to load knowledge from {}: {}", KNOWLEDGE_PATH, e.getMessage());
        }
    }

    /**
     * Process a query through the LangGraph workflow.
     */
    public Map<String, Object> process(String query) {
        WorkflowState state = new WorkflowState();
        state.set("query", query);
        long start = System.currentTimeMillis();

        state = workflow.invoke(state);

        long elapsed = System.currentTimeMillis() - start;
        return Map.of(
                "query", query,
                "clean_query", state.getString("clean_query"),
                "intent", state.getString("intent"),
                "has_pii", Boolean.TRUE.equals(state.get("has_pii")),
                "final_output", state.getString("final_output"),
                "elapsed_ms", elapsed
        );
    }

    /**
     * Node 2c: Memory intent — detect forget/remember/disable actions.
     */
    private WorkflowState handleMemory(WorkflowState state) {
        String query = state.getString("clean_query");

        if (query.contains("忘记") || query.contains("别记") || query.contains("别记下")) {
            state.set("memory_action", "forget");
            state.set("memory_response", "系统已记录：相关内容将不被保存到长期记忆中。");
        } else if (query.contains("禁用") || query.contains("不需要") || query.contains("别用")) {
            state.set("memory_action", "disable");
            state.set("memory_response", "系统已记录：该偏好已禁用。");
        } else if (query.contains("启用")) {
            state.set("memory_action", "enable");
            state.set("memory_response", "系统已记录：该偏好已启用。");
        } else if (query.contains("记住") || query.contains("偏好")) {
            state.set("memory_action", "remember");
            state.set("memory_response", "系统已记录：该偏好已保存到长期记忆中。");
        } else {
            state.set("memory_action", "query");
            state.set("memory_response", "未找到相关记忆记录。");
        }
        return state;
    }

    public boolean isKnowledgeReady() {
        return knowledgeRetriever.isReady();
    }
}
