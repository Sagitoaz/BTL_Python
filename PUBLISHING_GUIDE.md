# 📦 Hướng dẫn Publish Extension lên VS Code Marketplace

Guide này hướng dẫn chi tiết cách publish extension lên VS Code Marketplace và update phiên bản mới.

---

## 📋 Prerequisites

### 1. Cài đặt vsce (Visual Studio Code Extensions CLI)

```bash
npm install -g vsce
```

### 2. Tạo Publisher Account

1. Truy cập: https://marketplace.visualstudio.com/manage
2. Login bằng Microsoft/GitHub account
3. Click "Create publisher"
4. Điền thông tin:
   - **Publisher ID**: `Sagitoaz` (hoặc tên bạn muốn, không đổi được sau này)
   - **Publisher name**: "Sagito" (hiển thị trên marketplace)
   - **Email**: Your email

### 3. Tạo Personal Access Token (PAT)

1. Truy cập: https://dev.azure.com/
2. Chọn organization của bạn (hoặc tạo mới)
3. Click vào **User Settings** (góc phải) → **Personal access tokens**
4. Click **+ New Token**
5. Điền:
   - **Name**: "VS Code Extension Publishing"
   - **Organization**: All accessible organizations
   - **Expiration**: 1 year (hoặc custom)
   - **Scopes**: Chọn **Custom defined** → chỉ tick **Marketplace** → **Manage**
6. Click **Create** và **COPY TOKEN** (chỉ hiện 1 lần!)

---

## 🚀 Publishing Lần Đầu

### Bước 1: Chuẩn bị Extension

```bash
cd /home/sagito/Desktop/BTL_Python

# Đảm bảo code đã compile
npm install
npm run compile

# Kiểm tra không có errors
npm run compile
```

### Bước 2: Review package.json

Đảm bảo các fields quan trọng đã đúng:

```json
{
  "name": "btl-python-ai-coder",
  "displayName": "BTL Python AI Coder",
  "description": "🤖 Personalized AI code completion...",
  "version": "1.0.0",
  "publisher": "Sagitoaz",  // ← Phải match với Publisher ID bạn tạo
  "icon": "images/icon.png",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/Sagitoaz/BTL_Python.git"
  }
}
```

### Bước 3: Test Package Locally

```bash
# Package thành .vsix file
vsce package

# Sẽ tạo file: btl-python-ai-coder-1.0.0.vsix

# Test install local
code --install-extension btl-python-ai-coder-1.0.0.vsix

# Test extension hoạt động:
# 1. Mở Python file
# 2. Gõ code xem có suggestion không
# 3. Test commands: BTL: View My Coding Profile
```

### Bước 4: Login vào vsce

```bash
vsce login Sagitoaz
# Nhập Personal Access Token bạn đã copy ở trên
```

### Bước 5: Publish!

```bash
vsce publish
```

**Output sẽ giống:**
```
Publishing Sagitoaz.btl-python-ai-coder@1.0.0...
Successfully published Sagitoaz.btl-python-ai-coder@1.0.0!
```

### Bước 6: Verify trên Marketplace

1. Truy cập: https://marketplace.visualstudio.com/items?itemName=Sagitoaz.btl-python-ai-coder
2. Kiểm tra:
   - Icon hiển thị đúng
   - Description đầy đủ
   - Screenshots (nếu có)
   - README render đúng

---

## 🔄 Update Phiên Bản Mới

Khi có feature mới hoặc bug fix, làm theo steps sau:

### Bước 1: Update Code

```bash
# Make your changes
vim src/extension.ts
vim server/app/main.py
# etc...

# Commit changes
git add .
git commit -m "feat: add new feature XYZ"
```

### Bước 2: Update Version

Có 3 cách tăng version (theo [Semantic Versioning](https://semver.org/)):

```bash
# PATCH version (1.0.0 → 1.0.1) - Bug fixes
vsce publish patch

# MINOR version (1.0.0 → 1.1.0) - New features (backward compatible)
vsce publish minor

# MAJOR version (1.0.0 → 2.0.0) - Breaking changes
vsce publish major

# Hoặc specify version cụ thể:
vsce publish 1.2.3
```

**Lệnh này sẽ tự động:**
1. Tăng version trong `package.json`
2. Compile code
3. Package thành .vsix
4. Publish lên marketplace

### Bước 3: Update CHANGELOG.md

```bash
vim CHANGELOG.md
```

Thêm section mới:

```markdown
## [1.1.0] - 2025-01-XX

### Added
- New feature XYZ
- New command ABC

### Fixed
- Bug in DEF

### Changed
- Improved performance of GHI
```

### Bước 4: Commit Version Update

```bash
git add package.json CHANGELOG.md
git commit -m "chore: bump version to 1.1.0"
git push origin main
```

### Bước 5: Create GitHub Release (Optional)

1. Truy cập: https://github.com/Sagitoaz/BTL_Python/releases/new
2. Tag version: `v1.1.0`
3. Release title: `v1.1.0 - Feature XYZ`
4. Description: Copy từ CHANGELOG.md
5. Attach .vsix file
6. Publish release

---

## 📝 Publishing Checklist

Trước khi publish, check list này:

### Must Have ✅
- [ ] `package.json` có đầy đủ: name, displayName, description, version, publisher, icon, license, repository
- [ ] `README.md` có hướng dẫn sử dụng rõ ràng
- [ ] `CHANGELOG.md` updated với version mới
- [ ] `LICENSE` file exists (MIT)
- [ ] Icon file exists (`images/icon.png` - 128x128 PNG)
- [ ] Code compile không errors: `npm run compile`
- [ ] Test local: `code --install-extension btl-python-ai-coder-X.X.X.vsix`

### Nice to Have 🎨
- [ ] Screenshots trong README (demo extension hoạt động)
- [ ] Animated GIF showing features
- [ ] Gallery banner trong package.json
- [ ] Badges trong README (version, license, etc.)
- [ ] Contributing guidelines
- [ ] Code of conduct

---

## 🛠️ Troubleshooting

### Error: "Publisher 'Sagitoaz' not found"

**Fix:**
```bash
# Update package.json với publisher ID đúng
vim package.json
# Sửa "publisher": "Sagitoaz" thành publisher ID bạn đã tạo
```

### Error: "Personal Access Token is invalid"

**Fix:**
```bash
# Login lại với token mới
vsce login YourPublisherID
# Paste token mới
```

### Error: "Extension validation failed"

Check:
1. Icon file có tồn tại không: `ls images/icon.png`
2. package.json có syntax error không: `npm run compile`
3. `activationEvents` có đúng không

### Extension không hiện trên Marketplace sau publish

- Đợi 5-10 phút để marketplace index
- Clear browser cache
- Check email xem có rejection notice không

### Update không hiện cho users

- Users cần restart VS Code
- Hoặc manually check for updates: Extensions → ... → Check for Extension Updates

---

## 📊 Monitoring

### View Extension Statistics

1. Truy cập: https://marketplace.visualstudio.com/manage/publishers/Sagitoaz
2. Click vào extension name
3. Xem:
   - **Install count**
   - **Download count**
   - **Rating & Reviews**
   - **Q&A** (user questions)

### Respond to Reviews & Questions

- Login vào marketplace manage portal
- Vào tab "Q&A" hoặc "Reviews"
- Reply nhanh để tăng trust

---

## 🔒 Security Best Practices

### Protect Your PAT

```bash
# KHÔNG commit PAT vào git
# KHÔNG share PAT publicly
# Revoke PAT cũ nếu bị leak

# Store PAT an toàn:
# - Password manager (1Password, LastPass)
# - Environment variable (không commit .env)
```

### Review Code Before Publish

```bash
# Đảm bảo không có:
# - API keys hardcoded
# - Passwords/secrets
# - Debug logs với sensitive data

# Check git diff trước khi commit:
git diff
```

---

## 🎯 Tips for Success

### 1. Good README

- Clear description ngay đầu
- Animated GIF/screenshots
- Installation instructions
- Usage examples
- Keyboard shortcuts
- Settings documentation

### 2. Regular Updates

- Fix bugs quickly
- Release new features consistently
- Respond to issues on GitHub
- Update dependencies

### 3. Marketing

- Tweet about extension
- Post on Reddit r/vscode
- Write blog post
- Demo video on YouTube
- Share in Discord/Slack communities

### 4. Telemetry (Optional)

Add analytics để hiểu users sử dụng như thế nào:
- Application Insights
- Google Analytics
- Custom telemetry endpoint

**NOTE**: Phải tuân thủ privacy laws (GDPR, etc.)

---

## 📞 Support & Help

### VS Code Extension Docs
- https://code.visualstudio.com/api

### vsce Documentation
- https://github.com/microsoft/vscode-vsce

### Publisher Portal
- https://marketplace.visualstudio.com/manage

### Community
- VS Code Extension Slack
- Stack Overflow tag: vscode-extension
- GitHub Discussions

---

## 🎉 Success!

Sau khi publish, extension của bạn sẽ available trên:

**VS Code Marketplace:**
https://marketplace.visualstudio.com/items?itemName=Sagitoaz.btl-python-ai-coder

**Install command:**
```bash
ext install Sagitoaz.btl-python-ai-coder
```

**Trong VS Code:**
1. Open Extensions (`Ctrl+Shift+X`)
2. Search "BTL Python AI Coder"
3. Click Install

---

Made with ❤️ by Sagito
