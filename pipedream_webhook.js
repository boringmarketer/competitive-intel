// Minimal Pipedream Webhook for Slack Notifications
// Deploy this to Pipedream and use the webhook URL in your config

export default defineComponent({
  name: "Competitive Intel Slack Notifier",
  description: "Receives reports from competitive intelligence tool and posts to Slack",
  version: "1.0.0",
  
  props: {
    // HTTP trigger for receiving reports
    http: {
      type: "$.interface.http"
    },
    
    // Slack app for posting messages
    slack: {
      type: "app",
      app: "slack"
    },
    
    // Configuration
    slack_channel: {
      type: "string",
      label: "Slack Channel",
      description: "Channel to post reports (e.g., #competitive-intel)",
      default: "#general"
    },
    
    max_message_length: {
      type: "integer",
      label: "Max Message Length",
      description: "Maximum characters per Slack message",
      default: 3000
    }
  },

  async run({ steps, $ }) {
    const startTime = Date.now()
    
    try {
      console.log("📨 Received competitive intelligence report...")
      
      // Get report data from the trigger
      const requestBody = steps.trigger.event.body
      const { report, timestamp, source } = requestBody
      
      if (!report) {
        console.log("❌ No report data received")
        return $.respond({
          status: 400,
          body: { error: "No report data provided" }
        })
      }
      
      console.log(`📊 Processing report from ${source || 'unknown'} at ${timestamp}`)
      
      // Truncate report if too long for Slack
      let slackMessage = report
      if (report.length > this.max_message_length) {
        slackMessage = report.substring(0, this.max_message_length - 100) + "\n\n...(truncated - see full report in tool)"
      }
      
      // Format for Slack
      const formattedMessage = `${slackMessage}

---
📊 **Report Generated**: ${timestamp ? new Date(timestamp).toLocaleString() : 'Unknown time'}
🔧 **Source**: ${source || 'Competitive Intel Tool'}
⚡ **Processing Time**: ${Date.now() - startTime}ms`

      // Send to Slack
      console.log(`📱 Sending to Slack channel: ${this.slack_channel}`)
      
      const slackResponse = await $.send.http({
        method: "POST",
        url: "https://slack.com/api/chat.postMessage",
        headers: {
          "Authorization": `Bearer ${this.slack.$auth.oauth_access_token}`,
          "Content-Type": "application/json"
        },
        data: {
          channel: this.slack_channel,
          text: formattedMessage,
          username: "Competitive Intel Bot",
          icon_emoji: ":dart:",
          unfurl_links: false,
          unfurl_media: false
        }
      })

      if (!slackResponse.ok) {
        console.log("❌ Slack API error:", slackResponse.error)
        throw new Error(`Slack error: ${JSON.stringify(slackResponse.error)}`)
      }
      
      console.log("✅ Report sent to Slack successfully!")
      
      return {
        success: true,
        timestamp: new Date().toISOString(),
        slack_channel: this.slack_channel,
        message_length: formattedMessage.length,
        processing_time_ms: Date.now() - startTime,
        slack_message_ts: slackResponse.ts
      }
      
    } catch (error) {
      console.error("❌ Webhook processing failed:", error)
      
      // Try to send error notification to Slack
      try {
        await $.send.http({
          method: "POST",
          url: "https://slack.com/api/chat.postMessage",
          headers: {
            "Authorization": `Bearer ${this.slack.$auth.oauth_access_token}`,
            "Content-Type": "application/json"
          },
          data: {
            channel: this.slack_channel,
            text: `🚨 **Competitive Intel Webhook Error**\n\n**Error**: ${error.message}\n**Time**: ${new Date().toLocaleTimeString()}`,
            username: "Competitive Intel Bot",
            icon_emoji: ":warning:"
          }
        })
      } catch (slackError) {
        console.error("Failed to send error to Slack:", slackError)
      }
      
      return $.respond({
        status: 500,
        body: {
          success: false,
          error: error.message,
          timestamp: new Date().toISOString()
        }
      })
    }
  }
})