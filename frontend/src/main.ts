import { createApp } from 'vue'
import { ElAlert, ElButton } from 'element-plus'
import 'element-plus/theme-chalk/base.css'
import 'element-plus/theme-chalk/el-alert.css'
import 'element-plus/theme-chalk/el-button.css'
import 'element-plus/theme-chalk/el-message.css'
import App from './App.vue'
import './styles.css'

const app = createApp(App)
app.component('ElAlert', ElAlert)
app.component('ElButton', ElButton)
app.mount('#app')
