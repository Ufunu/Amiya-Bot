import os
import base64

from amiyabot.network.download import download_async
from core import app, bot
from core.database.plugin import PluginConfiguration

from .__model__ import BaseModel


class GetConfigModel(BaseModel):
    plugin_id: str


class SetConfigModel(BaseModel):
    plugin_id: str
    channel_id: str
    config_json: str


class InstallModel(BaseModel):
    url: str
    packageName: str


class UpgradeModel(BaseModel):
    url: str
    packageName: str
    plugin_id: str


class UninstallModel(BaseModel):
    plugin_id: str


@app.controller
class Plugin:
    @app.route(method='get')
    async def get_installed_plugin(self):
        res = []

        for _, item in bot.plugins.items():
            doc = item.document
            if os.path.isfile(doc):
                with open(doc, mode='r', encoding='utf-8') as file:
                    content = file.read()
            else:
                content = doc

            logo = ''
            if item.path:
                item_path = item.path[-1]
                logo_path = os.path.join(item_path, 'logo.png')
                if os.path.exists(logo_path):
                    with open(logo_path, mode='rb') as ico:
                        logo = 'data:image/png;base64,' + base64.b64encode(ico.read()).decode()

            res.append({
                'name': item.name,
                'version': item.version,
                'plugin_id': item.plugin_id,
                'plugin_type': item.plugin_type,
                'description': item.description,
                'document': content,
                'logo': logo
            })

        return app.response(res)

    @app.route(method='get')
    async def get_plugin_default_config(self, data: GetConfigModel):
        plugin = next((item for _, item in bot.plugins.items() if item.plugin_id == data.plugin_id), None)
        if not plugin:
            return app.response(code=500, message='未安装该插件')

        global_cfg = getattr(plugin, 'default_global_config', '{}')
        global_template = getattr(plugin, 'global_config_template', '{}')
        channel_cfg = getattr(plugin, 'default_channel_config', '{}')
        channel_template = getattr(plugin, 'channel_config_template', '{}')

        return app.response({
            'default_global_config': global_cfg,
            'global_config_template': global_template,
            'default_channel_config': channel_cfg,
            'channel_config_template': channel_template
        })

    @app.route(method='get')
    async def get_plugin_config(self, data: GetConfigModel):
        plugin = next((item for _, item in bot.plugins.items() if item.plugin_id == data.plugin_id), None)
        if not plugin:
            return app.response(code=500, message='未安装该插件')

        configs = PluginConfiguration.select().where(PluginConfiguration.plugin_id == plugin.plugin_id)

        config_dict = {}
        for cfg in configs:
            if cfg.channel_id:
                config_dict[cfg.channel_id] = cfg.json_config

        return app.response(config_dict)

    @app.route()
    async def set_plugin_config(self, data: SetConfigModel):
        plugin = next((item for _, item in bot.plugins.items() if item.plugin_id == data.plugin_id), None)
        if not plugin:
            return app.response(code=500, message='未安装该插件')

        config = PluginConfiguration.get_or_none(plugin_id=plugin.plugin_id, channel_id=data.channel_id)
        if not config:
            config = PluginConfiguration(plugin_id=plugin.plugin_id, channel_id=data.channel_id)

        config.json_config = data.config_json
        config.save()

        return app.response(message='配置已保存')

    @app.route()
    async def install_plugin(self, data: InstallModel):
        res = await download_async(data.url)
        if res:
            plugin = f'plugins/{data.packageName}'
            with open(plugin, mode='wb+') as src:
                src.write(res)

            if bot.install_plugin(plugin, extract_plugin=True):
                return app.response(message='插件安装成功')
            else:
                return app.response(code=500, message='插件安装失败')
        return app.response(code=500, message='插件下载失败')

    @app.route()
    async def upgrade_plugin(self, data: UpgradeModel):
        res = await download_async(data.url)
        if res:
            plugin = f'plugins/{data.packageName}'
            with open(plugin, mode='wb+') as src:
                src.write(res)

            bot.uninstall_plugin(data.plugin_id, remove=True)
            if bot.install_plugin(plugin, extract_plugin=True):
                return app.response(message='插件更新成功')
            else:
                return app.response(code=500, message='插件安装失败')
        return app.response(code=500, message='插件下载失败')

    @app.route()
    async def uninstall_plugin(self, data: UninstallModel):
        bot.uninstall_plugin(data.plugin_id, remove=True)

        return app.response(message='插件卸载成功')
