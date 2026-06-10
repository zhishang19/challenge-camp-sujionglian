package com.yupi.aicodehelper.ai.workflow;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * LangGraph workflow state container.
 */
public class WorkflowState {

    private final Map<String, Object> data = new LinkedHashMap<>();

    public WorkflowState() {
        data.put("pii_detections", new ArrayList<>());
        data.put("retrieved", new ArrayList<>());
    }

    @SuppressWarnings("unchecked")
    public <T> T get(String key) {
        return (T) data.get(key);
    }

    public void set(String key, Object value) {
        data.put(key, value);
    }

    public String getString(String key) {
        Object v = data.get(key);
        return v != null ? v.toString() : "";
    }

    @SuppressWarnings("unchecked")
    public List<String> getStringList(String key) {
        Object v = data.get(key);
        if (v instanceof List<?>) {
            return (List<String>) v;
        }
        return new ArrayList<>();
    }

    @SuppressWarnings("unchecked")
    public <T> List<T> getList(String key) {
        Object v = data.get(key);
        if (v instanceof List<?>) {
            return (List<T>) v;
        }
        return new ArrayList<>();
    }
}
