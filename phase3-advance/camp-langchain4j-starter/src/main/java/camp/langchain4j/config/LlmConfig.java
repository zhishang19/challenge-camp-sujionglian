package camp.langchain4j.config;

import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.model.ollama.OllamaChatModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

@Configuration
public class LlmConfig {

    @Value("${camp.llm.provider:ollama}")
    private String provider;

    @Value("${OLLAMA_BASE_URL:http://localhost:11434}")
    private String ollamaBaseUrl;

    @Value("${OLLAMA_MODEL:qwen2.5:7b}")
    private String ollamaModel;

    @Value("${OPENAI_API_KEY:}")
    private String openaiApiKey;

    @Value("${OPENAI_BASE_URL:https://api.openai.com}")
    private String openaiBaseUrl;

    @Value("${OPENAI_MODEL:gpt-4o-mini}")
    private String openaiModel;

    @Bean
    public ChatLanguageModel chatLanguageModel() {
        if ("openai".equalsIgnoreCase(provider)) {
            return OpenAiChatModel.builder()
                    .apiKey(openaiApiKey)
                    .baseUrl(openaiBaseUrl)
                    .modelName(openaiModel)
                    .timeout(Duration.ofSeconds(120))
                    .build();
        }
        return OllamaChatModel.builder()
                .baseUrl(ollamaBaseUrl)
                .modelName(ollamaModel)
                .timeout(Duration.ofSeconds(120))
                .build();
    }
}
