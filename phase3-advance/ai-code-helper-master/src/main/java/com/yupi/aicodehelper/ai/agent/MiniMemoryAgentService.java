package com.yupi.aicodehelper.ai.agent;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.File;
import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Mini Memory Agent — integration of personal data, preferences, and retrieval.
 *
 * Features:
 *   - Bigram-based knowledge retrieval with synonym expansion
 *   - PII redaction (email, phone, id_card, ip)
 *   - Forget / remember intent detection
 *   - Preference injection per user
 *   - User isolation by uid
 *   - Memory snapshots query
 */
@Slf4j
@Service
public class MiniMemoryAgentService {

    // ---- PII Patterns ----
    private static final Pattern EMAIL_RE = Pattern.compile(
            "[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+");
    private static final Pattern PHONE_RE = Pattern.compile("1[3-9]\\d{9}");
    private static final Pattern ID_CARD_RE = Pattern.compile("\\b\\d{17}[\\dXx]\\b");
    private static final Pattern IP_RE = Pattern.compile(
            "\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b");

    // ---- Forget / Remember Keywords ----
    private static final Set<String> FORGET_KW = Set.of(
            "别记", "忘记", "忘掉", "不保存", "删除", "不要记录", "别记下");
    private static final Set<String> REMEMBER_KW = Set.of(
            "记住", "偏好", "以后都", "总是", "永久", "习惯", "喜欢");

    // ---- Synonym Map for bigram expansion ----
    private static final Map<String, List<String>> SYNONYM_MAP = new LinkedHashMap<>();

    static {
        SYNONYM_MAP.put("月报", List.of("会议纪要", "月度报告"));
        SYNONYM_MAP.put("周报", List.of("会议纪要", "周度报告"));
        SYNONYM_MAP.put("会议纪要", List.of("月报", "周报", "会议记录"));
        SYNONYM_MAP.put("驱动", List.of("驱动更新", "驱动管理器", "安装驱动"));
        SYNONYM_MAP.put("麒麟", List.of("麒麟系统"));
        SYNONYM_MAP.put("离线安装", List.of("dpkg", "离线部署"));
        SYNONYM_MAP.put("deb", List.of("dpkg"));
        SYNONYM_MAP.put("dpkg", List.of("离线安装", "deb"));
        SYNONYM_MAP.put("文档导出", List.of("导出PDF", "导出"));
        SYNONYM_MAP.put("wps", List.of("word", "文档"));
        SYNONYM_MAP.put("隐私", List.of("设置", "敏感"));
        SYNONYM_MAP.put("别记", List.of("忘记", "不保存"));
    }

    private final ObjectMapper objectMapper = new ObjectMapper();

    // ---- Loaded data ----
    private List<Map<String, Object>> knowledgeItems = new ArrayList<>();
    private List<Map<String, Object>> preferences = new ArrayList<>();
    private List<Map<String, Object>> snapshots = new ArrayList<>();
    private List<Map<String, Object>> chatTurns = new ArrayList<>();
    private List<Map<String, Object>> toolExecutions = new ArrayList<>();
    private List<Map<String, Object>> memoryEvents = new ArrayList<>();

    private final Set<String> forgottenSet = new HashSet<>(); // "<uid>::<key>"

    private static final String DATA_DIR = "../../phase2-consolidate";

    @PostConstruct
    public void init() {
        log.info("Initializing Mini Memory Agent from: {}", new File(DATA_DIR).getAbsolutePath());
        knowledgeItems = loadJson("knowledge_items.json");
        preferences = loadJson("preferences.json");
        snapshots = loadJson("memory_snapshots_resolved.json");
        chatTurns = loadJson("chat_turns.json");
        toolExecutions = loadJson("tool_executions.json");
        memoryEvents = loadJson("memory_events.json");

        log.info("Mini Memory Agent loaded: knowledge={}, prefs={}, snapshots={}, chat={}, tools={}, events={}",
                knowledgeItems.size(), preferences.size(), snapshots.size(),
                chatTurns.size(), toolExecutions.size(), memoryEvents.size());
    }

    private List<Map<String, Object>> loadJson(String filename) {
        File file = new File(DATA_DIR, filename);
        if (!file.exists()) {
            log.warn("Data file not found: {}", file.getAbsolutePath());
            return new ArrayList<>();
        }
        try {
            return objectMapper.readValue(file, new TypeReference<>() {});
        } catch (Exception e) {
            log.error("Failed to load {}: {}", filename, e.getMessage());
            return new ArrayList<>();
        }
    }

    // ═══════════════════════════════════════════════
    // Public API
    // ═══════════════════════════════════════════════

    /**
     * Main query endpoint: process user input with all agent features.
     */
    public Map<String, Object> query(String uid, String userInput) {
        uid = normalizeUid(uid);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("uid", uid);
        result.put("query", userInput);

        // 1. PII redaction
        PiiResult pii = redactPii(userInput);
        String cleanQuery = pii.cleanText;
        result.put("has_pii", pii.hasPii);
        if (pii.hasPii) {
            result.put("pii_types", pii.types);
        }

        // 2. Forget intent detection
        boolean isForget = detectForgetIntent(cleanQuery);
        result.put("forget_detected", isForget);
        if (isForget) {
            forgottenSet.add(uid + "::" + (cleanQuery.length() > 40 ? cleanQuery.substring(0, 40) : cleanQuery));
            result.put("response", "[隐私保护] 该信息包含敏感内容，已被标记为不记录。");
            return result;
        }

        // 3. Knowledge retrieval (bigram + synonym)
        List<Map<String, Object>> searchResults = searchKnowledge(cleanQuery);
        result.put("knowledge_results", searchResults);
        result.put("knowledge_count", searchResults.size());

        // 4. Preference injection
        List<Map<String, Object>> userPrefs = getPreferences(uid);
        result.put("preferences_loaded", !userPrefs.isEmpty());
        result.put("preferences_count", userPrefs.size());
        if (!userPrefs.isEmpty()) {
            result.put("preferences", userPrefs.stream()
                    .map(p -> Map.of("key", p.getOrDefault("key", ""),
                                     "value", p.getOrDefault("value", ""),
                                     "version", p.getOrDefault("version", "")))
                    .collect(Collectors.toList()));
        }

        // 5. Memory snapshots for current user
        List<Map<String, Object>> userSnapshots = getSnapshots(uid);
        result.put("snapshot_count", userSnapshots.size());

        // 6. Remember detection
        boolean isRemember = detectRememberIntent(cleanQuery);
        result.put("remember_detected", isRemember);

        return result;
    }

    /**
     * Search-only mode for automated testing (5 test cases).
     */
    public List<Map<String, Object>> search(String query) {
        return searchKnowledge(query);
    }

    /**
     * Get preferences for a specific user.
     */
    public List<Map<String, Object>> getPreferences(String uid) {
        uid = normalizeUid(uid);
        String finalUid = uid;
        return preferences.stream()
                .filter(p -> normalizeUid(String.valueOf(p.getOrDefault("uid", ""))).equals(finalUid))
                .collect(Collectors.toList());
    }

    /**
     * Get memory snapshots for a specific user.
     */
    public List<Map<String, Object>> getSnapshots(String uid) {
        uid = normalizeUid(uid);
        String finalUid = uid;
        return snapshots.stream()
                .filter(s -> normalizeUid(String.valueOf(s.getOrDefault("uid", ""))).equals(finalUid))
                .collect(Collectors.toList());
    }

    /**
     * Get agent statistics.
     */
    public Map<String, Object> getStats() {
        return Map.of(
                "knowledge_items", knowledgeItems.size(),
                "preferences", preferences.size(),
                "snapshots", snapshots.size(),
                "chat_turns", chatTurns.size(),
                "tool_executions", toolExecutions.size(),
                "memory_events", memoryEvents.size(),
                "forgotten_items", forgottenSet.size()
        );
    }

    // ═══════════════════════════════════════════════
    // PII Redaction
    // ═══════════════════════════════════════════════

    private PiiResult redactPii(String text) {
        List<String> types = new ArrayList<>();
        String clean = text;

        if (EMAIL_RE.matcher(clean).find()) {
            types.add("email");
            clean = EMAIL_RE.matcher(clean).replaceAll("[EMAIL]");
        }
        if (PHONE_RE.matcher(clean).find()) {
            types.add("phone");
            clean = PHONE_RE.matcher(clean).replaceAll("[PHONE]");
        }
        if (ID_CARD_RE.matcher(clean).find()) {
            types.add("id_card");
            clean = ID_CARD_RE.matcher(clean).replaceAll("[ID_CARD]");
        }
        if (IP_RE.matcher(clean).find()) {
            types.add("ip_address");
            clean = IP_RE.matcher(clean).replaceAll("[IP]");
        }

        return new PiiResult(clean, !types.isEmpty(), types);
    }

    private static class PiiResult {
        final String cleanText;
        final boolean hasPii;
        final List<String> types;

        PiiResult(String cleanText, boolean hasPii, List<String> types) {
            this.cleanText = cleanText;
            this.hasPii = hasPii;
            this.types = types;
        }
    }

    // ═══════════════════════════════════════════════
    // Intent Detection
    // ═══════════════════════════════════════════════

    private boolean detectForgetIntent(String text) {
        return FORGET_KW.stream().anyMatch(text::contains);
    }

    private boolean detectRememberIntent(String text) {
        return REMEMBER_KW.stream().anyMatch(text::contains);
    }

    // ═══════════════════════════════════════════════
    // Bigram Knowledge Retrieval
    // ═══════════════════════════════════════════════

    private List<Map<String, Object>> searchKnowledge(String query) {
        List<String> expanded = expandSynonyms(query);
        List<ScoredItem> scored = new ArrayList<>();

        for (int i = 0; i < knowledgeItems.size(); i++) {
            Map<String, Object> item = knowledgeItems.get(i);
            String body = buildItemBody(item);
            double best = 0.0;
            for (String eq : expanded) {
                double s = bigramSimilarity(eq, body);
                best = Math.max(best, s);
            }
            if (best > 0.03) {
                scored.add(new ScoredItem(i, item, Math.round(best * 10000.0) / 10000.0));
            }
        }

        scored.sort((a, b) -> Double.compare(b.score, a.score));
        return scored.stream()
                .limit(5)
                .map(s -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("item_id", s.item.getOrDefault("item_id", "?"));
                    m.put("title", s.item.getOrDefault("title", ""));
                    m.put("body", buildItemBody(s.item));
                    m.put("score", s.score);
                    return m;
                })
                .collect(Collectors.toList());
    }

    private String buildItemBody(Map<String, Object> item) {
        String title = String.valueOf(item.getOrDefault("title", ""));
        @SuppressWarnings("unchecked")
        List<String> tags = (List<String>) item.getOrDefault("tags", Collections.emptyList());
        String body = String.valueOf(item.getOrDefault("body_clean", ""));
        return title + " " + String.join(" ", tags) + " " + body;
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
        if (bgA.isEmpty() || bgB.isEmpty()) return 0.0;
        Set<String> intersection = new LinkedHashSet<>(bgA);
        intersection.retainAll(bgB);
        Set<String> union = new LinkedHashSet<>(bgA);
        union.addAll(bgB);
        return (double) intersection.size() / union.size();
    }

    private static class ScoredItem {
        final int index;
        final Map<String, Object> item;
        final double score;

        ScoredItem(int index, Map<String, Object> item, double score) {
            this.index = index;
            this.item = item;
            this.score = score;
        }
    }

    private String normalizeUid(String uid) {
        return uid != null ? uid.toLowerCase().trim() : "u001";
    }
}
