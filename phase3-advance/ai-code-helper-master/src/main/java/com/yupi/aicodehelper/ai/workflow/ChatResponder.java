package com.yupi.aicodehelper.ai.workflow;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * Node 2b: Casual chat responses.
 */
@Slf4j
@Component
public class ChatResponder {

    private static final Map<String, String> REPLIES = Map.of(
            "你好", "你好！有什么可以帮助你的？",
            "谢谢", "不客气！",
            "再见", "再见，祝你生活愉快！",
            "嗨", "嗨！请问有什么需要？",
            "hello", "Hello! How can I help you?",
            "hi", "Hi! What can I do for you?",
            "bye", "Goodbye!"
    );

    public WorkflowState respond(WorkflowState state) {
        String query = state.getString("clean_query").trim();
        String reply = REPLIES.getOrDefault(query,
                "你好，我是编程小助手，专注于编程学习与求职面试相关问题。");
        state.set("chat_reply", reply);
        log.info("[chat] {}", reply);
        return state;
    }
}
