use schemars::JsonSchema;
use serde::Deserialize;
use zed::settings::ContextServerSettings;
use zed_extension_api::{
    self as zed, serde_json, Command, ContextServerConfiguration, ContextServerId, Project, Result,
};

#[derive(Debug, Default, Deserialize, JsonSchema)]
struct HoudiniMcpSettings {
    /// Absolute path to Python interpreter. Defaults to `python` on PATH.
    python_path: Option<String>,
    /// Houdini bridge host (default 127.0.0.1).
    host: Option<String>,
    /// Houdini bridge port (default 18812).
    port: Option<u16>,
    /// Use in-process mock backend instead of a live Houdini session.
    #[serde(default)]
    mock: bool,
    /// Extra args appended after `python -m houdini_mcp`.
    extra_args: Option<Vec<String>>,
}

fn non_empty(value: Option<String>) -> Option<String> {
    value.filter(|v| !v.trim().is_empty())
}

struct HoudiniMcpExtension;

impl zed::Extension for HoudiniMcpExtension {
    fn new() -> Self {
        Self
    }

    fn context_server_command(
        &mut self,
        _context_server_id: &ContextServerId,
        project: &Project,
    ) -> Result<Command> {
        let settings = ContextServerSettings::for_project("houdini-mcp", project)?;
        let settings: HoudiniMcpSettings = match settings.settings {
            Some(value) => serde_json::from_value(value).map_err(|e| e.to_string())?,
            None => HoudiniMcpSettings::default(),
        };

        let (platform, _arch) = zed::current_platform();
        let python = non_empty(settings.python_path).unwrap_or_else(|| match platform {
            // Prefer the Windows py launcher when no explicit interpreter is set.
            zed::Os::Windows => "py".to_string(),
            _ => "python3".to_string(),
        });

        let mut args = if python == "py" {
            vec![
                "-3".to_string(),
                "-m".to_string(),
                "houdini_mcp".to_string(),
            ]
        } else {
            vec!["-m".to_string(), "houdini_mcp".to_string()]
        };

        let mut env = Vec::new();
        if let Some(host) = non_empty(settings.host) {
            env.push(("HOUDINI_MCP_HOST".into(), host));
        }
        if let Some(port) = settings.port {
            env.push(("HOUDINI_MCP_PORT".into(), port.to_string()));
        }
        if settings.mock {
            env.push(("HOUDINI_MCP_MOCK".into(), "1".into()));
            args.push("--mock".into());
        }
        if let Some(extra) = settings.extra_args {
            args.extend(extra);
        }

        Ok(Command {
            command: python,
            args,
            env,
        })
    }

    fn context_server_configuration(
        &mut self,
        _context_server_id: &ContextServerId,
        _project: &Project,
    ) -> Result<Option<ContextServerConfiguration>> {
        let installation_instructions =
            include_str!("../configuration/installation_instructions.md").to_string();
        let default_settings =
            include_str!("../configuration/default_settings.jsonc").to_string();
        let settings_schema =
            serde_json::to_string(&schemars::schema_for!(HoudiniMcpSettings))
                .map_err(|e| e.to_string())?;

        Ok(Some(ContextServerConfiguration {
            installation_instructions,
            default_settings,
            settings_schema,
        }))
    }
}

zed::register_extension!(HoudiniMcpExtension);
