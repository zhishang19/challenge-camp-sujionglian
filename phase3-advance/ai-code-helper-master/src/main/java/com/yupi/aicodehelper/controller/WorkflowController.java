package com.yupi.aicodehelper.controller;

import com.yupi.aicodehelper.ai.agent.MiniMemoryAgentService;
import com.yupi.aicodehelper.ai.workflow.WorkflowService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * REST controller for LangGraph workflow & Mini Memory Agent.
 */
@Slf4j
@RestController
@RequestMapping("/d8d9")
public class WorkflowController {

    private final WorkflowService workflowService;
    private final MiniMemoryAgentService agentService;

    public WorkflowController(WorkflowService workflowService,
                              MiniMemoryAgentService agentService) {
        this.workflowService = workflowService;
        this.agentService = agentService;
    }

    // ═══════════════════════════════════════════════
    // LangGraph Workflow (D08) endpoints
    // ═══════════════════════════════════════════════

    /**
     * GET /api/d8d9/workflow?q=... — Process query through 3-node LangGraph workflow
     */
    @GetMapping("/workflow")
    public ResponseEntity<Map<String, Object>> workflow(
            @RequestParam(value = "q", defaultValue = "") String query) {
        if (query.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of("error", "Query parameter 'q' is required"));
        }
        Map<String, Object> result = workflowService.process(query);
        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/d8d9/workflow/demo — Run the full demo suite
     */
    @GetMapping("/workflow/demo")
    public ResponseEntity<Map<String, Object>> workflowDemo() {
        List<String> queries = List.of(
                "麒麟系统如何更新驱动？",
                "怎么写月报摘要？",
                "你好",
                "怎么离线安装.deb软件包？",
                "liubei@shu.com 帮我导出PDF",
                "以后回复别用emoji",
                "记住我喜欢详细输出带表格",
                "192.168.1.100 连不上了",
                "帮我查13812345678"
        );

        List<Map<String, Object>> results = new ArrayList<>();
        for (String q : queries) {
            Map<String, Object> r = workflowService.process(q);
            results.add(r);
        }

        return ResponseEntity.ok(Map.of(
                "total", queries.size(),
                "knowledge_loaded", workflowService.isKnowledgeReady(),
                "results", results
        ));
    }

    // ═══════════════════════════════════════════════
    // Mini Memory Agent (D09) endpoints
    // ═══════════════════════════════════════════════

    /**
     * GET /api/d8d9/agent/query?uid=...&q=... — Mini Memory Agent query
     */
    @GetMapping("/agent/query")
    public ResponseEntity<Map<String, Object>> agentQuery(
            @RequestParam(value = "uid", defaultValue = "u001") String uid,
            @RequestParam(value = "q", defaultValue = "") String q) {
        if (q.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of("error", "Query parameter 'q' is required"));
        }
        return ResponseEntity.ok(agentService.query(uid, q));
    }

    /**
     * GET /api/d8d9/agent/prefs?uid=... — Get user preferences
     */
    @GetMapping("/agent/prefs")
    public ResponseEntity<Map<String, Object>> agentPrefs(
            @RequestParam(value = "uid", defaultValue = "u001") String uid) {
        List<Map<String, Object>> prefs = agentService.getPreferences(uid);
        return ResponseEntity.ok(Map.of(
                "uid", uid,
                "count", prefs.size(),
                "preferences", prefs
        ));
    }

    /**
     * GET /api/d8d9/agent/snapshots?uid=... — Get user memory snapshots
     */
    @GetMapping("/agent/snapshots")
    public ResponseEntity<Map<String, Object>> agentSnapshots(
            @RequestParam(value = "uid", defaultValue = "u001") String uid) {
        List<Map<String, Object>> snaps = agentService.getSnapshots(uid);
        return ResponseEntity.ok(Map.of(
                "uid", uid,
                "count", snaps.size(),
                "snapshots", snaps
        ));
    }

    /**
     * GET /api/d8d9/agent/stats — Agent statistics
     */
    @GetMapping("/agent/stats")
    public ResponseEntity<Map<String, Object>> agentStats() {
        return ResponseEntity.ok(agentService.getStats());
    }

    /**
     * GET /api/d8d9/agent/test — Run 5 test cases (D09 TEST.md)
     */
    @GetMapping("/agent/test")
    public ResponseEntity<Map<String, Object>> agentTest() {
        TestResult result = runTestCases();
        return ResponseEntity.ok(Map.of(
                "total", result.total,
                "passed", result.passed,
                "all_passed", result.passed == result.total,
                "results", result.results
        ));
    }

    // ═══════════════════════════════════════════════
    // Test Cases (D09 — 5 test cases)
    // ═══════════════════════════════════════════════

    private static class TestCase {
        int id;
        String uid;
        String query;
        String description;
        List<String> expectedKnowledgeKeywords;
        boolean checkPref;
        boolean checkPii;
        boolean checkForget;
        String checkMemory;

        TestCase(int id, String uid, String query, String description) {
            this.id = id;
            this.uid = uid;
            this.query = query;
            this.description = description;
        }
    }

    private static class TestResult {
        int total;
        int passed = 0;
        List<Map<String, Object>> results = new ArrayList<>();
    }

    private TestResult runTestCases() {
        List<TestCase> cases = buildTestCases();
        TestResult summary = new TestResult();
        summary.total = cases.size();

        for (TestCase tc : cases) {
            Map<String, Object> tcResult = new LinkedHashMap<>();
            tcResult.put("id", tc.id);
            tcResult.put("uid", tc.uid);
            tcResult.put("query", tc.query);
            tcResult.put("description", tc.description);

            boolean passed = true;
            Map<String, Object> queryResult = agentService.query(tc.uid, tc.query);

            // Check: knowledge keywords
            if (tc.expectedKnowledgeKeywords != null && !tc.expectedKnowledgeKeywords.isEmpty()) {
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> knowledgeResults =
                        (List<Map<String, Object>>) queryResult.getOrDefault("knowledge_results", List.of());
                if (knowledgeResults.isEmpty()) {
                    tcResult.put("knowledge_check", "FAIL — no results");
                    passed = false;
                } else {
                    List<String> bodies = knowledgeResults.stream()
                            .map(r -> String.valueOf(r.getOrDefault("body", "")))
                            .collect(java.util.stream.Collectors.toList());
                    List<String> matched = tc.expectedKnowledgeKeywords.stream()
                            .filter(kw -> bodies.stream().anyMatch(b -> b.contains(kw)))
                            .collect(java.util.stream.Collectors.toList());
                    if (matched.isEmpty()) {
                        tcResult.put("knowledge_check", "FAIL — keywords not found: " + tc.expectedKnowledgeKeywords);
                        passed = false;
                    } else {
                        tcResult.put("knowledge_check", "PASS — matched: " + matched);
                    }
                }
            }

            // Check: preferences
            if (tc.checkPref) {
                @SuppressWarnings("unchecked")
                boolean prefsLoaded = (boolean) queryResult.getOrDefault("preferences_loaded", false);
                tcResult.put("preference_check", prefsLoaded ? "PASS" : "FAIL");
                if (!prefsLoaded) passed = false;
            }

            // Check: PII
            if (tc.checkPii) {
                @SuppressWarnings("unchecked")
                boolean hasPii = (boolean) queryResult.getOrDefault("has_pii", false);
                tcResult.put("pii_check", hasPii ? "PASS" : "FAIL");
                if (!hasPii) passed = false;
            }

            // Check: forget
            if (tc.checkForget) {
                @SuppressWarnings("unchecked")
                boolean forgetDetected = (boolean) queryResult.getOrDefault("forget_detected", false);
                tcResult.put("forget_check", forgetDetected ? "PASS" : "FAIL");
                if (!forgetDetected) passed = false;
            }

            // Check: memory snapshots
            if (tc.checkMemory != null) {
                List<Map<String, Object>> snaps = agentService.getSnapshots(tc.checkMemory);
                boolean hasSnapshots = !snaps.isEmpty();
                tcResult.put("memory_check", hasSnapshots ? "PASS — " + snaps.size() + " snapshot(s)" : "FAIL");
                if (!hasSnapshots) passed = false;
            }

            tcResult.put("passed", passed);
            summary.results.add(tcResult);
            if (passed) summary.passed++;
        }

        return summary;
    }

    private List<TestCase> buildTestCases() {
        List<TestCase> cases = new ArrayList<>();

        // Test 1: U0001 query about kirin system driver update
        TestCase tc1 = new TestCase(1, "U0001",
                "麒麟系统如何更新驱动？",
                "U0001 麒麟系统如何更新驱动 → 知识检索+偏好注入(U0001有output_style)");
        tc1.checkPref = true;
        cases.add(tc1);

        // Test 2: U0001 write monthly report summary → synonym expansion
        TestCase tc2 = new TestCase(2, "U0001",
                "写月报摘要",
                "U0001 写月报摘要 → 同义词扩展(月报→会议纪要)");
        tc2.expectedKnowledgeKeywords = List.of("会议纪要");
        tc2.checkPref = true;
        cases.add(tc2);

        // Test 3: U0002 greeting → emoji_policy preference + snapshots
        TestCase tc3 = new TestCase(3, "U0002",
                "你好",
                "U0002 你好 → 偏好加载 + 记忆快照");
        tc3.checkPref = true;
        tc3.checkMemory = "U0002";
        cases.add(tc3);

        // Test 4: U0003 offline deb install → synonym expansion
        TestCase tc4 = new TestCase(4, "U0003",
                "怎么离线安装.deb软件包？",
                "U0003 怎么离线安装.deb软件包 → 同义词扩展(deb→dpkg/离线安装)");
        tc4.expectedKnowledgeKeywords = List.of("离线安装", "deb");
        cases.add(tc4);

        // Test 5: U0004 email + forget → PII redaction + forget
        TestCase tc5 = new TestCase(5, "U0004",
                "liubei@shu.com 别记下这个邮箱",
                "U0004 邮箱+别记下 → PII脱敏+forget");
        tc5.checkPii = true;
        tc5.checkForget = true;
        cases.add(tc5);

        return cases;
    }
}
