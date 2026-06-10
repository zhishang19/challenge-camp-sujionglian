package camp.langchain4j.controller;

import camp.langchain4j.service.PreferenceLoader;
import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.data.message.SystemMessage;
import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.model.output.Response;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class ChatController {

    private final ChatLanguageModel chatModel;
    private final PreferenceLoader preferenceLoader;

    public ChatController(ChatLanguageModel chatModel, PreferenceLoader preferenceLoader) {
        this.chatModel = chatModel;
        this.preferenceLoader = preferenceLoader;
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }

    @GetMapping("/chat")
    public Map<String, String> chat(
            @RequestParam String q,
            @RequestParam(defaultValue = "u001") String uid) {
        SystemMessage systemMessage = preferenceLoader.getSystemMessage(uid);
        UserMessage userMessage = UserMessage.userMessage(q);
        Response<AiMessage> response = chatModel.generate(systemMessage, userMessage);
        return Map.of(
                "question", q,
                "uid", uid,
                "answer", response.content().text());
    }

    @GetMapping("/chat/system")
    public Map<String, String> chatSystem(
            @RequestParam(defaultValue = "u001") String uid) {
        String systemText = preferenceLoader.getSystemMessageText(uid);
        return Map.of(
                "uid", uid,
                "systemMessage", systemText);
    }

    @PostMapping("/chat/preference")
    public Map<String, String> chatWithPreference(
            @RequestBody PreferenceRequest request,
            @RequestParam(defaultValue = "u001") String uid) {
        SystemMessage systemMessage = preferenceLoader.getSystemMessage(uid);
        String prefInstruction = request.getPreference() != null
                ? request.getPreference() : "";
        String fullSystemText = systemMessage.text();
        if (!prefInstruction.isBlank()) {
            fullSystemText = fullSystemText + "；另外请注意：" + prefInstruction;
        }
        UserMessage userMessage = UserMessage.userMessage(request.getQuestion());
        Response<AiMessage> response = chatModel.generate(
                SystemMessage.systemMessage(fullSystemText), userMessage);
        return Map.of(
                "question", request.getQuestion(),
                "uid", uid,
                "preference", prefInstruction,
                "answer", response.content().text());
    }

    public static class PreferenceRequest {
        private String question;
        private String preference;

        public String getQuestion() { return question; }
        public void setQuestion(String question) { this.question = question; }
        public String getPreference() { return preference; }
        public void setPreference(String preference) { this.preference = preference; }
    }
}
