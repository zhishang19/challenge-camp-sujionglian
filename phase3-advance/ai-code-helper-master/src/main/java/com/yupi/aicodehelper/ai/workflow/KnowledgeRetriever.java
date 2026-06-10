package com.yupi.aicodehelper.ai.workflow;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;

/**
 * Node 2a: Knowledge retrieval using bigram similarity + synonym expansion.
 * Knowledge source: phase2-consolidate/knowledge_items.json (D4 cleaned results)
 */
@Slf4j
@Component
public class KnowledgeRetriever {

    // Synonym map for query expansion
    private static final Map<String, List<String>> SYNONYM_MAP = new LinkedHashMap<>();

    static {
        SYNONYM_MAP.put("月报", List.of("会议纪要", "月度报告"));
        SYNONYM_MAP.put("周报", List.of("会议纪要", "周度报告"));
        SYNONYM_MAP.put("会议纪要", List.of("月报", "周报", "会议记录"));
        SYNONYM_MAP.put("驱动", List.of("驱动更新", "驱动安装"));
        SYNONYM_MAP.put("麒麟", List.of("麒麟系统"));
        SYNONYM_MAP.put("离线安装", List.of("dpkg", "离线部署"));
        SYNONYM_MAP.put("deb", List.of("dpkg"));
        SYNONYM_MAP.put("dpkg", List.of("deb", "离线安装"));
        SYNONYM_MAP.put("文档导出", List.of("导出PDF", "导出"));
        SYNONYM_MAP.put("wps", List.of("word", "文档"));
    }

    private List<KnowledgeItem> knowledgeItems = new ArrayList<>();

    public void loadKnowledge(List<Map<String, Object>> rawItems) {
        this.knowledgeItems = new ArrayList<>();
        for (Map<String, Object> raw : rawItems) {
            KnowledgeItem item = new KnowledgeItem();
            item.id = String.valueOf(raw.getOrDefault("item_id", "?"));
            item.title = String.valueOf(raw.getOrDefault("title", ""));
            item.body = String.valueOf(raw.getOrDefault("body_clean", ""));
            @SuppressWarnings("unchecked")
            List<String> tags = (List<String>) raw.getOrDefault("tags", Collections.emptyList());
            item.tags = tags;
            item.bodyText = item.title + " " + String.join(" ", item.tags) + " " + item.body;
            this.knowledgeItems.add(item);
        }
        log.info("Loaded {} knowledge items for workflow", this.knowledgeItems.size());
    }

    public boolean isReady() {
        return !knowledgeItems.isEmpty();
    }

    public WorkflowState retrieve(WorkflowState state) {
        String query = state.getString("clean_query");
        if (query.isEmpty()) {
            query = state.getString("query");
        }

        List<KnowledgeHit> results = searchKnowledge(query);
        state.set("retrieved", results);

        if (!results.isEmpty()) {
            log.info("[retrieve] Top {} match(es) for query", results.size());
        } else {
            log.info("[retrieve] No match found");
        }
        return state;
    }

    private List<KnowledgeHit> searchKnowledge(String query) {
        List<String> expanded = expandSynonyms(query);

        List<KnowledgeHit> scored = new ArrayList<>();
        for (KnowledgeItem item : knowledgeItems) {
            double best = 0.0;
            for (String eq : expanded) {
                double s = bigramSimilarity(eq, item.bodyText);
                best = Math.max(best, s);
            }
            if (best > 0.03) {
                scored.add(new KnowledgeHit(item, Math.round(best * 10000.0) / 10000.0));
            }
        }
        scored.sort((a, b) -> Double.compare(b.score, a.score));
        return scored.size() > 5 ? scored.subList(0, 5) : scored;
    }

    private List<String> expandSynonyms(String query) {
        List<String> expansions = new ArrayList<>();
        expansions.add(query);
        for (var entry : SYNONYM_MAP.entrySet()) {
            if (query.contains(entry.getKey())) {
                for (String syn : entry.getValue()) {
                    if (!query.contains(syn)) {
                        expansions.add(query.replace(entry.getKey(), syn));
                    }
                }
            }
        }
        return expansions;
    }

    private Set<String> buildBigrams(String text) {
        String cleaned = text.replace(" ", "").toLowerCase();
        Set<String> bigrams = new LinkedHashSet<>();
        if (cleaned.length() < 2) {
            bigrams.add(cleaned);
            return bigrams;
        }
        for (int i = 0; i < cleaned.length() - 1; i++) {
            bigrams.add(cleaned.substring(i, i + 2));
        }
        return bigrams;
    }

    private double bigramSimilarity(String a, String b) {
        Set<String> bgA = buildBigrams(a);
        Set<String> bgB = buildBigrams(b);
        if (bgA.isEmpty() || bgB.isEmpty()) {
            return 0.0;
        }
        Set<String> intersection = new LinkedHashSet<>(bgA);
        intersection.retainAll(bgB);
        Set<String> union = new LinkedHashSet<>(bgA);
        union.addAll(bgB);
        return (double) intersection.size() / union.size();
    }

    // ---- Data classes ----

    public static class KnowledgeItem {
        public String id;
        public String title;
        public String body;
        public List<String> tags;
        public String bodyText;
    }

    public static class KnowledgeHit {
        public KnowledgeItem item;
        public double score;

        public KnowledgeHit(KnowledgeItem item, double score) {
            this.item = item;
            this.score = score;
        }
    }
}
