package com.yupi.aicodehelper.ai.workflow;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Function;

/**
 * Lightweight state graph polyfill — simulates LangGraph's StateGraph.
 * Supports nodes, conditional edges, direct edges, and entry/finish points.
 */
public class SimpleStateGraph {

    private final Map<String, Function<WorkflowState, WorkflowState>> nodes = new LinkedHashMap<>();
    private final Map<String, Function<WorkflowState, String>> conditions = new LinkedHashMap<>();
    private final Map<String, Map<String, String>> routes = new LinkedHashMap<>();
    private final Map<String, String> edges = new LinkedHashMap<>();
    private String entry;
    private String finish;

    public SimpleStateGraph addNode(String name, Function<WorkflowState, WorkflowState> func) {
        nodes.put(name, func);
        return this;
    }

    public SimpleStateGraph setEntryPoint(String name) {
        this.entry = name;
        return this;
    }

    public SimpleStateGraph setFinishPoint(String name) {
        this.finish = name;
        return this;
    }

    public SimpleStateGraph addEdge(String from, String to) {
        edges.put(from, to);
        return this;
    }

    /**
     * Add conditional routing from a node.
     * @param from     source node name
     * @param cond     function that returns the branch key
     * @param routeMap mapping from branch key → target node name
     */
    public SimpleStateGraph addConditionalEdges(String from,
                                                 Function<WorkflowState, String> cond,
                                                 Map<String, String> routeMap) {
        conditions.put(from, cond);
        routes.put(from, routeMap);
        return this;
    }

    public WorkflowState invoke(WorkflowState state) {
        String current = entry;
        while (current != null && !current.equals(finish)) {
            Function<WorkflowState, WorkflowState> nodeFunc = nodes.get(current);
            if (nodeFunc == null) {
                break;
            }
            state = nodeFunc.apply(state);

            // Check conditional edges first
            if (conditions.containsKey(current)) {
                String branch = conditions.get(current).apply(state);
                Map<String, String> routeMap = routes.get(current);
                current = routeMap.getOrDefault(branch, null);
            } else {
                // Use direct edge
                current = edges.get(current);
            }
        }
        // Execute finish node if exists
        if (current != null && nodes.containsKey(current)) {
            state = nodes.get(current).apply(state);
        }
        return state;
    }
}
