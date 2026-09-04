import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import test from 'node:test'

const frontend=readFileSync(new URL('./src/HrCenterPage.tsx',import.meta.url),'utf8')
const backend=readFileSync(new URL('../api-server/app/main.py',import.meta.url),'utf8')

test('员工头像的前后端格式契约一致并优先于普通附件白名单',()=>{
  for(const mime of ['image/png','image/jpeg','image/gif','image/webp'])assert.match(frontend,new RegExp(mime.replace('/','\\/')))
  for(const suffix of ['.png','.jpg','.jpeg','.gif','.webp'])assert.match(backend,new RegExp(`"\\${suffix}"`))
  const avatarGuard=backend.indexOf('is_employee_avatar = bool(')
  const ordinaryGuard=backend.indexOf('if not is_employee_avatar and (not record or record.module != "case") and suffix not in allowed:')
  const avatarValidation=backend.indexOf('if is_employee_avatar:',ordinaryGuard)
  assert.ok(avatarGuard>=0&&ordinaryGuard>avatarGuard&&avatarValidation>ordinaryGuard)
})

test('员工头像拒绝非图片、伪造图片和超限文件',()=>{
  assert.match(backend,/not str\(file\.content_type or ""\)\.lower\(\)\.startswith\("image\/"\)/)
  assert.match(backend,/if not image_signature_valid:/)
  assert.match(backend,/len\(content\) > 5 \* 1024 \* 1024/)
  assert.match(frontend,/头像仅支持 PNG、JPG、GIF 或 WebP 图片/)
})

test('头像预览 Object URL 在更换与组件卸载时释放',()=>{
  assert.match(frontend,/useEffect\(\(\)=>\(\)=>\{if\(avatarPreview\)URL\.revokeObjectURL\(avatarPreview\)\},\[avatarPreview\]\)/)
})
