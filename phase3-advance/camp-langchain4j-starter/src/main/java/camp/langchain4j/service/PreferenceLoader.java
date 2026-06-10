package camp.langchain4j.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.data.message.SystemMessage;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class PreferenceLoader {

    private static final Logger log = LoggerFactory.getLogger(PreferenceLoader.class);

    private final Map<String, List<Preference>> preferencesByUid = new HashMap<>();

    private final ObjectMapper objectMapper = new ObjectMapper();

    @PostConstruct
    public void init() {
        List<String> paths = Arrays.asList(
                "preferences.json",
                "data/preferences.json",
                "config/preferences.json"
        );
        for (String path : paths) {
            try {
                ClassPathResource resource = new ClassPathResource(path);
                if (resource.exists()) {
                    try (InputStream is = resource.getInputStream()) {
                        List<Preference> allPreferences = objectMapper.readValue(
                                is, new TypeReference<List<Preference>>() {});
                        for (Preference pref : allPreferences) {
                            String uidLower = pref.getUid().toLowerCase();
                            preferencesByUid
                                    .computeIfAbsent(uidLower, k -> new ArrayList<>())
                                    .add(pref);
                        }
                        log.info("Loaded {} preferences from classpath:{}",
                                allPreferences.size(), path);
                        return;
                    }
                }
            } catch (Exception e) {
                log.warn("Failed to load preferences from classpath:{}: {}", path, e.getMessage());
            }
        }
        log.warn("No preferences.json found on classpath. Using empty preferences.");
    }

    public SystemMessage getSystemMessage(String uid) {
        if (uid == null || uid.isBlank()) {
            return SystemMessage.systemMessage("你是一个有帮助的助手。");
        }
        List<Preference> prefs = preferencesByUid.get(uid.toLowerCase());
        if (prefs == null || prefs.isEmpty()) {
            return SystemMessage.systemMessage("你是一个有帮助的助手。");
        }
        String instructions = prefs.stream()
                .map(p -> {
                    if (p.getPrefKey() != null && !"unknown".equalsIgnoreCase(p.getPrefKey())) {
                        return p.getPrefKey() + "：" + p.getPrefValue();
                    }
                    return p.getPrefValue();
                })
                .collect(Collectors.joining("；"));
        return SystemMessage.systemMessage(
                "请根据以下用户偏好回答问题：" + instructions);
    }

    public String getSystemMessageText(String uid) {
        return getSystemMessage(uid).text();
    }

    public String getAllPreferencesJson() {
        List<Preference> all = new ArrayList<>();
        for (List<Preference> list : preferencesByUid.values()) {
            all.addAll(list);
        }
        try {
            return objectMapper.writeValueAsString(all);
        } catch (Exception e) {
            return "[]";
        }
    }

    public static class Preference {
        private String uid;
        private String pref_key;
        private String pref_value;
        private String type;
        private String version;
        private String source;
        private String time;
        private String ttl;
        private String confidence;

        public String getUid() { return uid; }
        public void setUid(String uid) { this.uid = uid; }
        public String getPrefKey() { return pref_key; }
        public void setPrefKey(String pref_key) { this.pref_key = pref_key; }
        public String getPrefValue() { return pref_value; }
        public void setPrefValue(String pref_value) { this.pref_value = pref_value; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public String getVersion() { return version; }
        public void setVersion(String version) { this.version = version; }
        public String getSource() { return source; }
        public void setSource(String source) { this.source = source; }
        public String getTime() { return time; }
        public void setTime(String time) { this.time = time; }
        public String getTtl() { return ttl; }
        public void setTtl(String ttl) { this.ttl = ttl; }
        public String getConfidence() { return confidence; }
        public void setConfidence(String confidence) { this.confidence = confidence; }
    }
}
