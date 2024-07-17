#include <Arduino.h>


String file_contents = "";
bool automode = false;


String createFolder(String path) {
  return "Folder created: " + path;
}

// Função para simular a criação de um arquivo
String createFile(String path, String content = "") {
  file_contents = content;
  return "File created and added to system prompt: " + path;
}
String updateSystemPrompt(int current_iteration, int max_iterations) {
  String chain_of_thought_prompt = "";
  String file_contents_prompt = "\n\nFile Contents:\n";
  file_contents_prompt += file_contents + "\n";

  String BASE_SYSTEM_PROMPT = "Base system prompt";
  String AUTOMODE_SYSTEM_PROMPT = "Automode system prompt";

  if (automode) {
    String iteration_info = "You are currently on iteration " + String(current_iteration) + " out of " + String(max_iterations) + " in automode.";
    return BASE_SYSTEM_PROMPT + file_contents_prompt + "\n\n" + AUTOMODE_SYSTEM_PROMPT + iteration_info + "\n\n" + chain_of_thought_prompt;
  } else {
    return BASE_SYSTEM_PROMPT + file_contents_prompt + "\n\n" + chain_of_thought_prompt;
  }
}

void setup() {
  Serial.begin(9600);

  // Exemplo de uso das funções
  Serial.println(createFolder("/example_folder"));
  Serial.println(createFile("/example_folder/example_file.txt", "Hello, Arduino!"));
  Serial.println(updateSystemPrompt(1, 10));
}

void loop() {
  // Código principal do Arduino
}
