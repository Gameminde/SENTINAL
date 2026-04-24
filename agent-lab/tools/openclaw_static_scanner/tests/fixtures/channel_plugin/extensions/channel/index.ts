export function activate(api: any) {
  api.registerChannel("fakechat", {
    async sendMessage(target: string, text: string) {
      await fetch("https://example.test/messages", { method: "POST", body: text });
    }
  });
}
