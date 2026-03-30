#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <cctype>
#include <iomanip>
#include <windows.h>
#include <conio.h>

using namespace std;

// ==================== 常量定义 ====================
const int KEYWORD_START = 1;
const int ID_CODE = 20;
const int NUM_CODE = 30;
const int OP_START = 40;
const int DELIM_START = 60;
const int STR_CODE = 80;
const int ERROR_CODE = 99;

// ==================== 数据结构 ====================

// 关键字表
map<string, int> keywordTable = {
    {"if", 1}, {"else", 2}, {"while", 3}, {"do", 4},
    {"for", 5}, {"int", 6}, {"float", 7}, {"char", 8},
    {"return", 9}, {"void", 10}, {"main", 11}, {"printf", 12}
};

// 单词结构
struct Token {
    string word;        // 单词
    int code;           // 种别码
    int line;           // 行号
    int col;            // 列号
    string type;        // 类型描述
};

// 错误信息结构
struct ErrorInfo {
    int line;
    int col;
    string msg;
    char ch;
};

// ==================== 全局变量 ====================
ifstream sourceFile;
ofstream resultFile;
vector<Token> tokenList;
vector<ErrorInfo> errorList;
int lineNum = 1;
int colNum = 0;
char currentChar = ' ';
bool visualizeMode = true;
int delayMs = 500;  // 可视化延迟

// ==================== 可视化工具函数 ====================

// 设置控制台颜色
void setColor(int color) {
    SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE), color);
}

// 恢复默认颜色
void resetColor() {
    SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE), 7);
}

// 清屏
void clearScreen() {
    system("cls");
}

// 在指定位置打印
void gotoxy(int x, int y) {
    COORD coord;
    coord.X = x;
    coord.Y = y;
    SetConsoleOutputCP(65001); // UTF-8
    SetConsoleCursorPosition(GetStdHandle(STD_OUTPUT_HANDLE), coord);
}

// 延迟
void delay(int ms) {
    Sleep(ms);
}

// 打印分隔线
void printLine(char c, int len) {
    for (int i = 0; i < len; i++) cout << c;
    cout << endl;
}

// ==================== 可视化显示函数 ====================

void showState(const string& state, const string& details, int color = 7) {
    if (!visualizeMode) return;
    
    gotoxy(0, 0);
    clearScreen();
    
    setColor(11);
    cout << "╔══════════════════════════════════════════════════════════════╗" << endl;
    cout << "║              C语言词法分析器 - 实时可视化演示                ║" << endl;
    cout << "╚══════════════════════════════════════════════════════════════╝" << endl;
    resetColor();
    
    cout << "\n【当前状态】";
    setColor(color);
    cout << " " << state << endl;
    resetColor();
    
    cout << "\n【详细信息】" << endl;
    cout << details << endl;
    
    cout << "\n【统计信息】" << endl;
    cout << "  当前行号: " << lineNum << "  列号: " << colNum << endl;
    cout << "  已识别单词数: " << tokenList.size() << endl;
    cout << "  错误数: " << errorList.size() << endl;
    
    cout << "\n【最近识别的单词】" << endl;
    int start = max(0, (int)tokenList.size() - 5);
    for (int i = start; i < tokenList.size(); i++) {
        cout << "  [" << setw(2) << i+1 << "] " << left << setw(15) 
             << tokenList[i].word << " 种别码: " << tokenList[i].code 
             << " (" << tokenList[i].type << ")" << endl;
    }
    
    if (!errorList.empty()) {
        cout << "\n【错误信息】" << endl;
        setColor(12);
        for (const auto& err : errorList) {
            cout << "  错误 at (" << err.line << "," << err.col << "): " 
                 << err.msg << " [" << err.ch << "]" << endl;
        }
        resetColor();
    }
    
    delay(delayMs);
}

// ==================== 核心词法分析函数 ====================

// 读取下一个字符
void getChar() {
    if (sourceFile.get(currentChar)) {
        colNum++;
        if (currentChar == '\n') {
            lineNum++;
            colNum = 0;
        }
    } else {
        currentChar = EOF;
    }
}

// 回退字符
void ungetChar() {
    if (currentChar != EOF) {
        sourceFile.unget();
        if (currentChar == '\n') {
            lineNum--;
        } else {
            colNum--;
        }
    }
}

// 判断是否为字母或下划线
bool isLetter(char c) {
    return isalpha(c) || c == '_';
}

// 判断是否为数字
bool isDigit(char c) {
    return isdigit(c);
}

// 跳过空白字符和注释
void skipWhitespaceAndComments() {
    while (currentChar != EOF) {
        // 跳过空白
        if (isspace(currentChar)) {
            getChar();
            continue;
        }
        
        // 跳过单行注释 //
        if (currentChar == '/') {
            getChar();
            if (currentChar == '/') {
                showState("跳过注释", "检测到单行注释 //", 14);
                while (currentChar != '\n' && currentChar != EOF) {
                    getChar();
                }
                continue;
            } else if (currentChar == '*') {
                showState("跳过注释", "检测到多行注释 /* */", 14);
                // 跳过多行注释
                getChar();
                while (currentChar != EOF) {
                    if (currentChar == '*') {
                        getChar();
                        if (currentChar == '/') {
                            getChar();
                            break;
                        }
                    } else {
                        getChar();
                    }
                }
                continue;
            } else {
                ungetChar();
                currentChar = '/';
                break;
            }
        }
        break;
    }
}

// 识别标识符或关键字
Token recognizeIdentifier() {
    Token token;
    token.line = lineNum;
    token.col = colNum;
    token.word = "";
    
    string details = "开始识别标识符/关键字\n当前字符: ";
    details += currentChar;
    showState("识别标识符", details, 10);
    
    while (isLetter(currentChar) || isDigit(currentChar)) {
        token.word += currentChar;
        getChar();
    }
    
    // 查关键字表
    auto it = keywordTable.find(token.word);
    if (it != keywordTable.end()) {
        token.code = it->second;
        token.type = "关键字";
        showState("识别到关键字", "单词: " + token.word + "  种别码: " + to_string(token.code), 10);
    } else {
        token.code = ID_CODE;
        token.type = "标识符";
        showState("识别到标识符", "单词: " + token.word + "  种别码: " + to_string(token.code), 2);
    }
    
    return token;
}

// 识别普通数字（无符号）
Token recognizeNumber() {
    Token token;
    token.line = lineNum;
    token.col = colNum;
    token.word = "";
    token.type = "常数";
    
    showState("识别常数", "开始识别数字常数", 6);
    
    // 读取整数部分
    while (isDigit(currentChar)) {
        token.word += currentChar;
        getChar();
    }
    
    // 读取小数部分
    if (currentChar == '.') {
        token.word += currentChar;  // 添加小数点
        getChar();
        
        // 必须有小数部分
        if (!isDigit(currentChar)) {
            // 错误：小数点后没有数字
            ErrorInfo err = {lineNum, colNum, "小数点后必须有数字", currentChar};
            errorList.push_back(err);
            token.code = NUM_CODE;
            showState("错误：小数点后无数字", "位置: (" + to_string(lineNum) + "," + to_string(colNum) + ")", 12);
            return token;
        }
        
        while (isDigit(currentChar)) {
            token.word += currentChar;
            getChar();
        }
    }
    
    token.code = NUM_CODE;
    showState("识别到常数", "单词: " + token.word + "  种别码: " + to_string(token.code), 6);
    return token;
}

// 识别带符号的数字（+3.14, -5 等）
Token recognizeSignedNumber() {
    Token token;
    token.line = lineNum;
    token.col = colNum;
    token.word = "";
    token.type = "常数";
    
    string details = "开始识别带符号数字\n当前字符: ";
    details += currentChar;
    showState("识别带符号常数", details, 6);
    
    // 当前字符是 + 或 -
    token.word += currentChar;
    getChar(); // 读取符号后的第一个字符
    
    // 读取整数部分
    while (isDigit(currentChar)) {
        token.word += currentChar;
        getChar();
    }
    
    // 读取小数部分
    if (currentChar == '.') {
        token.word += currentChar;
        getChar();
        
        while (isDigit(currentChar)) {
            token.word += currentChar;
            getChar();
        }
    }
    
    token.code = NUM_CODE;
    showState("识别到带符号常数", "单词: " + token.word + "  种别码: " + to_string(token.code), 6);
    return token;
}

// 识别运算符
Token recognizeOperator() {
    Token token;
    token.line = lineNum;
    token.col = colNum;
    token.type = "运算符";
    
    char first = currentChar;
    token.word = string(1, first);
    getChar();
    
    // 检查双字符运算符
    string twoChar = token.word + currentChar;
    map<string, int> twoCharOps = {
        {"==", 41}, {"!=", 42}, {"<=", 43}, {">=", 44},
        {"&&", 45}, {"||", 46}, {"++", 47}, {"--", 48}
    };
    
    auto it = twoCharOps.find(twoChar);
    if (it != twoCharOps.end()) {
        token.word = twoChar;
        token.code = it->second;
        getChar();
    } else {
        // 单字符运算符
        map<char, int> singleCharOps = {
            {'+', 40}, {'-', 40}, {'*', 40}, {'/', 40}, {'%', 40},
            {'=', 50}, {'<', 51}, {'>', 52}, {'!', 53}, {'&', 54}, {'|', 55}
        };
        token.code = singleCharOps[first];
    }
    
    showState("识别到运算符", "单词: " + token.word + "  种别码: " + to_string(token.code), 5);
    return token;
}

// 识别界符
Token recognizeDelimiter() {
    Token token;
    token.line = lineNum;
    token.col = colNum;
    token.word = string(1, currentChar);
    token.type = "界符";
    
    map<char, int> delims = {
        {';', 60}, {',', 61}, {'(', 62}, {')', 63},
        {'{', 64}, {'}', 65}, {'[', 66}, {']', 67}
    };
    
    token.code = delims[currentChar];
    showState("识别到界符", "单词: " + token.word + "  种别码: " + to_string(token.code), 3);
    
    getChar();
    return token;
}

// 识别字符串
Token recognizeString() {
    Token token;
    token.line = lineNum;
    token.col = colNum;
    token.word = "\"";
    token.code = STR_CODE;
    token.type = "字符串";
    
    showState("识别字符串", "开始识别字符串常量", 13);
    
    getChar(); // 跳过左引号
    while (currentChar != '"' && currentChar != EOF && currentChar != '\n') {
        token.word += currentChar;
        getChar();
    }
    
    if (currentChar == '"') {
        token.word += "\"";
        getChar();
        showState("识别到字符串", "单词: " + token.word + "  种别码: " + to_string(token.code), 13);
    } else {
        // 字符串未闭合
        ErrorInfo err = {lineNum, colNum, "字符串未闭合", currentChar};
        errorList.push_back(err);
        showState("错误：字符串未闭合", "位置: (" + to_string(lineNum) + "," + to_string(colNum) + ")", 12);
    }
    
    return token;
}

// 错误处理
void handleError() {
    ErrorInfo err;
    err.line = lineNum;
    err.col = colNum;
    err.ch = currentChar;
    err.msg = "非法字符";
    errorList.push_back(err);
    
    string details = "发现非法字符: ";
    details += currentChar;
    details += " (ASCII: " + to_string((int)currentChar) + ")";
    showState("词法错误", details, 12);
    
    getChar(); // 跳过错误字符，实现错误恢复
}

// ==================== 主分析函数 ====================

void lexicalAnalysis() {
    showState("初始化", "词法分析器启动，准备扫描源文件...", 15);
    
    getChar(); // 读取第一个字符
    
    while (currentChar != EOF) {
        skipWhitespaceAndComments();
        
        if (currentChar == EOF) break;
        
        Token token;
        bool recognized = false;
        
        // 识别标识符或关键字
        if (isLetter(currentChar)) {
            token = recognizeIdentifier();
            recognized = true;
        }
        // 识别普通数字（无符号）
        else if (isDigit(currentChar)) {
            token = recognizeNumber();
            recognized = true;
        }
        // 识别带符号的数字（+5, -3.14）- 关键修复：检查+-后面是否是数字
        else if ((currentChar == '+' || currentChar == '-') && 
                 isDigit(static_cast<char>(sourceFile.peek()))) {
            token = recognizeSignedNumber();
            recognized = true;
        }
        // 识别字符串
        else if (currentChar == '"') {
            token = recognizeString();
            recognized = true;
        }
        // 识别运算符（单独的+-）
        else if (string("+-*/%=<>&|!").find(currentChar) != string::npos) {
            token = recognizeOperator();
            recognized = true;
        }
        // 识别界符
        else if (string(";,:(){}[]").find(currentChar) != string::npos) {
            token = recognizeDelimiter();
            recognized = true;
        }
        // 错误处理
        else {
            handleError();
            continue;
        }
        
        if (recognized) {
            tokenList.push_back(token);
            // 写入结果文件
            resultFile << "(" << token.word << ", " << token.code << ")" << endl;
        }
    }
    
    showState("分析完成", "词法分析结束，共识别 " + to_string(tokenList.size()) + " 个单词", 10);
}

// ==================== 输出报告 ====================

void printReport() {
    clearScreen();
    setColor(11);
    cout << "╔══════════════════════════════════════════════════════════════╗" << endl;
    cout << "║                    词法分析报告                              ║" << endl;
    cout << "╚══════════════════════════════════════════════════════════════╝" << endl;
    resetColor();
    
    cout << "\n【词法规则表】" << endl;
    printLine('=', 60);
    cout << "类别          种别码范围    说明" << endl;
    printLine('-', 60);
    cout << "关键字        1-12          if,else,while等12个" << endl;
    cout << "标识符        20            以字母或下划线开头的字符串" << endl;
    cout << "常数          30            整数、小数、带符号数" << endl;
    cout << "运算符        40-55         +,-,*,/,=,==,!=等" << endl;
    cout << "界符          60-67         ;,,(,),{,},[,]" << endl;
    cout << "字符串        80            \"...\"形式的字符串" << endl;
    cout << "错误          99            非法字符" << endl;
    printLine('=', 60);
    
    cout << "\n【关键字表】" << endl;
    printLine('=', 40);
    cout << "单词          种别码" << endl;
    printLine('-', 40);
    for (const auto& kw : keywordTable) {
        cout << left << setw(14) << kw.first << kw.second << endl;
    }
    printLine('=', 40);
    
    cout << "\n【识别结果】共 " << tokenList.size() << " 个单词" << endl;
    printLine('=', 70);
    cout << left << setw(5) << "序号" << setw(15) << "单词" << setw(10) << "种别码" 
         << setw(12) << "类型" << setw(10) << "行号" << "列号" << endl;
    printLine('-', 70);
    
    for (int i = 0; i < tokenList.size(); i++) {
        const auto& t = tokenList[i];
        cout << left << setw(5) << (i+1) << setw(15) << t.word << setw(10) << t.code 
             << setw(12) << t.type << setw(10) << t.line << t.col << endl;
    }
    printLine('=', 70);
    
    if (!errorList.empty()) {
        setColor(12);
        cout << "\n【错误列表】共 " << errorList.size() << " 个错误" << endl;
        printLine('=', 60);
        for (const auto& err : errorList) {
            cout << "位置(" << err.line << "," << err.col << "): " 
                 << err.msg << " [" << err.ch << "]" << endl;
        }
        printLine('=', 60);
        resetColor();
    } else {
        setColor(10);
        cout << "\n✓ 未发现词法错误！" << endl;
        resetColor();
    }
    
    cout << "\n结果已保存至 result.txt" << endl;
}

// ==================== 主函数 ====================

int main() {
    // 设置控制台代码页
    SetConsoleOutputCP(65001); // UTF-8
    SetConsoleCP(65001);
    
    cout << "C语言词法分析器" << endl;
    cout << "1. 实时可视化模式（较慢，用于演示）" << endl;
    cout << "2. 快速模式（直接输出结果）" << endl;
    cout << "请选择模式 (1/2): ";
    
    int mode;
    cin >> mode;
    visualizeMode = (mode == 1);
    
    if (visualizeMode) {
        cout << "请输入延迟时间(毫秒，建议100-1000): ";
        cin >> delayMs;
    }
    
    // 打开文件
    sourceFile.open("s.txt");
    if (!sourceFile.is_open()) {
        cerr << "错误：无法打开源文件 s.txt" << endl;
        
        // 创建示例文件
        ofstream example("s.txt");
        example << "int main() {\n";
        example << "    int ad = 10;\n";
        example << "    float bf = -3.14+ad;\n";
        example << "    if (ad > 5) {\n";
        example << "        printf(\"Hello World\");\n";
        example << "        ad++;\n";
        example << "    }\n";
        example << "    return 0;\n";
        example << "}\n";
        example.close();
        
        cout << "已创建示例文件 s.txt，请重新运行程序" << endl;
        return 1;
    }
    
    resultFile.open("result.txt");
    if (!resultFile.is_open()) {
        cerr << "错误：无法创建结果文件 result.txt" << endl;
        return 1;
    }
    
    // 执行词法分析
    lexicalAnalysis();
    
    // 关闭文件
    sourceFile.close();
    resultFile.close();
    
    // 输出报告
    printReport();
    
    cout << "\n按任意键退出...";
    _getch();
    
    return 0;
}