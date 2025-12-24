"""
Flask Web应用入口
"""
from flask import Flask, render_template
from .config import config
from .api.routes import register_routes

# 创建Flask应用
app = Flask(__name__, 
            template_folder='../../templates',
            static_folder='../../static')

# 存储提取的数据（临时）
extracted_data_cache = {}

# 注册路由
register_routes(app, extracted_data_cache)


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)


