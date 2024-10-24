import streamlit as st
import google.generativeai as genai
from datetime import datetime
import json
import hashlib
import os
from PIL import Image
import base64
import io

# API 키 설정
GOOGLE_API_KEY = "AIzaSyCMK8OG4m8rt4oATFGCSZ9z7BhJ6JwNXFI"
genai.configure(api_key=GOOGLE_API_KEY)

# 페이지 설정
st.set_page_config(
    page_title="AI 학습 도우미",
    page_icon="🎓",
    layout="wide",
    menu_items=None
)

# 파일 및 디렉토리 경로 설정
DATA_DIR = "data"
PROFILE_IMAGES_DIR = "profile_images"
LOG_DIR = "logs"

USERS_FILE = os.path.join(DATA_DIR, "users.json")
SESSION_FILE = os.path.join(DATA_DIR, "session.json")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
CHATS_FILE = os.path.join(DATA_DIR, "chats.json")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error_log.txt")

# 필요한 디렉토리 생성
for directory in [DATA_DIR, PROFILE_IMAGES_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)

# CSS 스타일
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .user-profile {
        padding: 20px;
        border-radius: 10px;
        background-color: #f8f9fa;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .profile-image {
        border-radius: 50%;
        margin: 10px auto;
        display: block;
    }
    .chat-message {
        padding: 10px;
        margin: 5px 0;
        border-radius: 10px;
        max-width: 80%;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
    }
    .other-message {
        background-color: #f5f5f5;
        margin-right: 20%;
    }
    .chat-list {
        border-right: 1px solid #ddd;
        height: 100%;
        padding-right: 20px;
    }
    .chat-container {
        height: 500px;
        overflow-y: auto;
        padding: 20px;
        border: 1px solid #ddd;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .stButton > button {
        background-color: #1f497d;
        color: white;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# 데이터 관리 클래스
class DataManager:
    @staticmethod
    def load_data(file_path, default=None):
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default if default is not None else {}
        except Exception as e:
            print(f"Error loading data from {file_path}: {e}")
            return default if default is not None else {}

    @staticmethod
    def save_data(file_path, data):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving data to {file_path}: {e}")
            return False

# 세션 관리 클래스
class SessionManager:
    @staticmethod
    def save_session():
        session_data = {
            'logged_in': st.session_state.logged_in,
            'current_user': st.session_state.current_user,
            'current_chat': st.session_state.get('current_chat'),
            'last_activity': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        DataManager.save_data(SESSION_FILE, session_data)

    @staticmethod
    def load_session():
        session_data = DataManager.load_data(SESSION_FILE, {
            'logged_in': False,
            'current_user': None,
            'current_chat': None,
            'last_activity': None
        })
        return session_data

# 에러 처리 클래스
class ErrorHandler:
    def __init__(self):
        self.log_file = ERROR_LOG_FILE

    def log_error(self, error_type, message, user=None):
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user_info = f"User: {user}" if user else "User: Not logged in"
            error_log = f"[{current_time}] {error_type}: {message} - {user_info}\n"
            
            with open(self.log_file, "a", encoding='utf-8') as f:
                f.write(error_log)
            
            return f"오류가 발생했습니다: {message}"
        except Exception as e:
            return f"로그 기록 중 오류 발생: {str(e)}"

# 유틸리티 함수들
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_ai_response(prompt):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}"

def save_profile_image(image_file, username):
    try:
        image_path = os.path.join(PROFILE_IMAGES_DIR, f"{username}.png")
        img = Image.open(image_file)
        img.save(image_path)
        return image_path
    except Exception as e:
        st.session_state.error_handler.log_error(
            "ImageError",
            f"프로필 이미지 저장 실패: {str(e)}",
            username
        )
        return None

# 세션 상태 초기화
if 'initialized' not in st.session_state:
    session_data = SessionManager.load_session()
    st.session_state.update(session_data)
    st.session_state.users = DataManager.load_data(USERS_FILE, {'users': {}})['users']
    st.session_state.groups = DataManager.load_data(GROUPS_FILE, {})
    st.session_state.chats = DataManager.load_data(CHATS_FILE, {})
    st.session_state.error_handler = ErrorHandler()
    st.session_state.initialized = True
# 사용자 관리 클래스
class UserManager:
    @staticmethod
    def register_user(username, password, email, nickname, profile_image=None):
        if username in st.session_state.users:
            return False, "이미 존재하는 아이디입니다."
        
        image_path = None
        if profile_image:
            image_path = save_profile_image(profile_image, username)
        
        st.session_state.users[username] = {
            'password': hash_password(password),
            'email': email,
            'nickname': nickname,
            'profile_image': image_path,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'study_records': [],
            'my_groups': [],
            'my_chats': []
        }
        DataManager.save_data(USERS_FILE, {'users': st.session_state.users})
        return True, "회원가입이 완료되었습니다!"

    @staticmethod
    def login_user(username, password):
        if username not in st.session_state.users:
            return False, "존재하지 않는 아이디입니다."
        
        user = st.session_state.users[username]
        if user['password'] == hash_password(password):
            st.session_state.logged_in = True
            st.session_state.current_user = username
            SessionManager.save_session()
            return True, "로그인 성공!"
        return False, "비밀번호가 일치하지 않습니다."

    @staticmethod
    def update_profile(username, updates):
        if username not in st.session_state.users:
            return False, "사용자를 찾을 수 없습니다."
        
        user = st.session_state.users[username]
        
        if 'new_password' in updates and updates['new_password']:
            user['password'] = hash_password(updates['new_password'])
        
        if 'nickname' in updates:
            user['nickname'] = updates['nickname']
        
        if 'email' in updates:
            user['email'] = updates['email']
        
        if 'profile_image' in updates and updates['profile_image']:
            image_path = save_profile_image(updates['profile_image'], username)
            if image_path:
                user['profile_image'] = image_path
        
        DataManager.save_data(USERS_FILE, {'users': st.session_state.users})
        return True, "프로필이 업데이트되었습니다!"

# 채팅 관리 클래스
class ChatManager:
    @staticmethod
    def create_chat(chat_name, creator, members):
        if chat_name in st.session_state.chats:
            return False, "이미 존재하는 채팅방 이름입니다."
        
        # 멤버 목록에 생성자 추가
        members = list(set(members + [creator]))
        
        st.session_state.chats[chat_name] = {
            'creator': creator,
            'members': members,
            'messages': [],
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        # 각 멤버의 채팅방 목록에 추가
        for member in members:
            if member in st.session_state.users:
                if 'my_chats' not in st.session_state.users[member]:
                    st.session_state.users[member]['my_chats'] = []
                st.session_state.users[member]['my_chats'].append(chat_name)
        
        DataManager.save_data(CHATS_FILE, st.session_state.chats)
        DataManager.save_data(USERS_FILE, {'users': st.session_state.users})
        return True, "채팅방이 생성되었습니다!"

    @staticmethod
    def add_message(chat_name, user, message):
        if chat_name not in st.session_state.chats:
            return False, "채팅방을 찾을 수 없습니다."
        
        chat = st.session_state.chats[chat_name]
        if user not in chat['members']:
            return False, "채팅방 멤버가 아닙니다."
        
        chat['messages'].append({
            'user': user,
            'message': message,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        DataManager.save_data(CHATS_FILE, st.session_state.chats)
        return True, "메시지가 전송되었습니다."

# 인증 페이지 표시 함수
def show_auth_page():
    tab1, tab2, tab3 = st.tabs(["로그인", "회원가입", "계정 찾기"])
    
    # 로그인 탭
    with tab1:
        st.header("로그인")
        with st.form("login_form"):
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인")
            
            if submitted:
                if not username or not password:
                    st.error("아이디와 비밀번호를 모두 입력해주세요.")
                else:
                    success, message = UserManager.login_user(username, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    
    # 회원가입 탭
    with tab2:
        st.header("회원가입")
        with st.form("register_form"):
            new_username = st.text_input("아이디")
            new_password = st.text_input("비밀번호", type="password")
            confirm_password = st.text_input("비밀번호 확인", type="password")
            email = st.text_input("이메일")
            nickname = st.text_input("닉네임")
            profile_image = st.file_uploader("프로필 이미지", type=['png', 'jpg', 'jpeg'])
            submitted = st.form_submit_button("회원가입")
            
            if submitted:
                if not all([new_username, new_password, email, nickname]):
                    st.error("모든 필수 항목을 입력해주세요.")
                elif new_password != confirm_password:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    success, message = UserManager.register_user(
                        new_username, new_password, email, nickname, profile_image
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

    # 계정 찾기 탭
    with tab3:
        st.header("계정 찾기")
        find_tab1, find_tab2 = st.tabs(["아이디 찾기", "비밀번호 찾기"])
        
        # 아이디 찾기
        with find_tab1:
            with st.form("find_id_form"):
                find_email = st.text_input("가입시 등록한 이메일")
                submitted = st.form_submit_button("아이디 찾기")
                
                if submitted and find_email:
                    found = False
                    for username, user in st.session_state.users.items():
                        if user['email'] == find_email:
                            st.success(f"귀하의 아이디는 {username} 입니다.")
                            found = True
                            break
                    if not found:
                        st.error("등록된 이메일을 찾을 수 없습니다.")
        
        # 비밀번호 찾기
        with find_tab2:
            with st.form("find_pw_form"):
                username = st.text_input("아이디")
                email = st.text_input("가입시 등록한 이메일")
                submitted = st.form_submit_button("비밀번호 재설정")
                
                if submitted and username and email:
                    if username in st.session_state.users:
                        user = st.session_state.users[username]
                        if user['email'] == email:
                            new_password = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
                            user['password'] = hash_password(new_password)
                            DataManager.save_data(USERS_FILE, {'users': st.session_state.users})
                            st.success(f"임시 비밀번호가 발급되었습니다: {new_password}")
                        else:
                            st.error("이메일이 일치하지 않습니다.")
                    else:
                        st.error("존재하지 않는 아이디입니다.")
# 프로필 페이지 표시 함수
def show_profile_page():
    user = st.session_state.users[st.session_state.current_user]
    
    st.title("내 프로필")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if user.get('profile_image'):
            st.image(user['profile_image'], width=200)
        else:
            st.image("https://via.placeholder.com/200", width=200)
        
        with st.expander("프로필 이미지 변경"):
            new_image = st.file_uploader("새 프로필 이미지", type=['png', 'jpg', 'jpeg'])
            if st.button("이미지 업데이트") and new_image:
                success, message = UserManager.update_profile(
                    st.session_state.current_user,
                    {'profile_image': new_image}
                )
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    with col2:
        st.markdown(f"""
        ### {user['nickname']}님의 프로필
        **아이디:** {st.session_state.current_user}  
        **이메일:** {user['email']}  
        **가입일:** {user['created_at']}
        """)
        
        with st.expander("프로필 수정"):
            new_nickname = st.text_input("새 닉네임", user['nickname'])
            new_email = st.text_input("새 이메일", user['email'])
            new_password = st.text_input("새 비밀번호", type="password")
            confirm_password = st.text_input("새 비밀번호 확인", type="password")
            
            if st.button("프로필 업데이트"):
                updates = {
                    'nickname': new_nickname,
                    'email': new_email
                }
                
                if new_password:
                    if new_password != confirm_password:
                        st.error("비밀번호가 일치하지 않습니다.")
                        return
                    updates['new_password'] = new_password
                
                success, message = UserManager.update_profile(
                    st.session_state.current_user,
                    updates
                )
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

# 학습 관리 클래스
class StudyManager:
    @staticmethod
    def add_study_record(username, record):
        if username not in st.session_state.users:
            return False, "사용자를 찾을 수 없습니다."
        
        user = st.session_state.users[username]
        if 'study_records' not in user:
            user['study_records'] = []
        
        user['study_records'].append({
            **record,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        DataManager.save_data(USERS_FILE, {'users': st.session_state.users})
        return True, "학습 기록이 저장되었습니다."

# 학습 페이지 표시 함수
def show_study_page():
    st.title("📚 개인 학습")
    
    subject = st.selectbox(
        "과목 선택",
        ["수학", "과학", "영어", "국어", "사회"]
    )
    
    study_mode = st.radio(
        "학습 모드 선택",
        ["개념 학습", "문제 풀이", "질문하기", "학습 기록"]
    )
    
    if study_mode == "개념 학습":
        topic = st.text_input("학습할 주제를 입력하세요:")
        level = st.select_slider("학습 난이도", ["기초", "보통", "심화"])
        
        if st.button("학습 시작") and topic:
            with st.spinner("AI가 학습 자료를 준비중입니다..."):
                prompt = f"""
                {subject} 과목의 '{topic}'에 대해 {level} 수준으로 설명해주세요.
                다음 내용을 포함해주세요:
                1. 핵심 개념 설명
                2. 주요 원리와 법칙
                3. 실생활 예시
                4. 관련 문제 예시
                """
                response = get_ai_response(prompt)
                st.markdown("### 📖 학습 내용:")
                st.markdown(response)
                
                success, message = StudyManager.add_study_record(
                    st.session_state.current_user,
                    {
                        'subject': subject,
                        'mode': '개념 학습',
                        'topic': topic,
                        'level': level
                    }
                )
                if not success:
                    st.error(message)
    
    elif study_mode == "문제 풀이":
        problem = st.text_area("문제를 입력하세요:")
        show_steps = st.checkbox("단계별 풀이 보기", value=True)
        
        if st.button("풀이 보기") and problem:
            with st.spinner("AI가 풀이를 준비중입니다..."):
                prompt = f"""
                다음 {subject} 문제를 {'단계별로 자세히' if show_steps else '간단히'} 풀어주세요:
                {problem}
                """
                response = get_ai_response(prompt)
                st.markdown("### ✏️ 풀이:")
                st.markdown(response)
                
                success, message = StudyManager.add_study_record(
                    st.session_state.current_user,
                    {
                        'subject': subject,
                        'mode': '문제 풀이',
                        'problem': problem[:100]
                    }
                )
                if not success:
                    st.error(message)
                
                # 유사 문제 생성
                if st.button("유사 문제 생성"):
                    with st.spinner("유사 문제를 생성중입니다..."):
                        similar_prompt = f"방금 풀이한 문제와 비슷한 난이도의 문제를 2개 만들어주세요. 각 문제의 풀이도 함께 제공해주세요."
                        similar_problems = get_ai_response(similar_prompt)
                        st.markdown("### 📝 유사 문제:")
                        st.markdown(similar_problems)
    
    elif study_mode == "질문하기":
        question = st.text_area("질문을 입력하세요:")
        include_examples = st.checkbox("예시 포함", value=True)
        
        if st.button("답변 받기") and question:
            with st.spinner("AI가 답변을 준비중입니다..."):
                prompt = f"""
                {subject} 관련 질문입니다: {question}
                {'예시를 포함하여 ' if include_examples else ''}자세히 답변해주세요.
                """
                response = get_ai_response(prompt)
                st.markdown("### 💡 답변:")
                st.markdown(response)
                
                success, message = StudyManager.add_study_record(
                    st.session_state.current_user,
                    {
                        'subject': subject,
                        'mode': '질문하기',
                        'question': question[:100]
                    }
                )
                if not success:
                    st.error(message)
    
    else:  # 학습 기록
        user = st.session_state.users[st.session_state.current_user]
        if user.get('study_records'):
            st.header("📊 학습 통계")
            records = user['study_records']
            
            # 과목별 학습 횟수
            subjects = {}
            modes = {}
            for record in records:
                subjects[record['subject']] = subjects.get(record['subject'], 0) + 1
                modes[record['mode']] = modes.get(record['mode'], 0) + 1
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("과목별 학습 횟수")
                st.bar_chart(subjects)
            with col2:
                st.subheader("학습 모드별 횟수")
                st.bar_chart(modes)
            
            # 최근 학습 기록
            st.header("📝 최근 학습 기록")
            for record in reversed(records[-10:]):
                with st.expander(f"{record['date']} - {record['subject']} ({record['mode']})"):
                    for key, value in record.items():
                        if key not in ['date', 'subject', 'mode']:
                            st.write(f"**{key}:** {value}")
        else:
            st.info("아직 학습 기록이 없습니다.")
# 스터디 그룹 페이지 표시 함수
def show_group_page():
    st.title("👥 스터디 그룹")
    
    tab1, tab2, tab3 = st.tabs([
        "그룹 관리", "학습 계획", "토론"
    ])
    
    user = st.session_state.users[st.session_state.current_user]
    
    # 그룹 관리 탭
    with tab1:
        st.header("📋 그룹 관리")
        
        # 새 그룹 생성
        with st.expander("새 스터디 그룹 만들기", expanded=True):
            group_name = st.text_input("그룹 이름")
            subject = st.selectbox("학습 과목", ["수학", "과학", "영어", "국어", "사회"])
            members = st.text_input("멤버 (쉼표로 구분)")
            description = st.text_area("그룹 설명")
            
            if st.button("그룹 만들기") and group_name and subject:
                members_list = [m.strip() for m in members.split(',')] if members else []
                members_list.append(st.session_state.current_user)  # 생성자 추가
                
                if group_name not in st.session_state.groups:
                    st.session_state.groups[group_name] = {
                        'name': group_name,
                        'creator': st.session_state.current_user,
                        'subject': subject,
                        'members': members_list,
                        'description': description,
                        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'plans': [],
                        'discussions': []
                    }
                    
                    if 'my_groups' not in user:
                        user['my_groups'] = []
                    user['my_groups'].append(group_name)
                    
                    DataManager.save_data(GROUPS_FILE, st.session_state.groups)
                    DataManager.save_data(USERS_FILE, {'users': st.session_state.users})
                    st.success(f"'{group_name}' 그룹이 생성되었습니다!")
                    st.rerun()
                else:
                    st.error("이미 존재하는 그룹 이름입니다.")
        
        # 내 그룹 목록
        if user.get('my_groups'):
            st.subheader("내 그룹 목록")
            for group_name in user['my_groups']:
                if group_name in st.session_state.groups:
                    group = st.session_state.groups[group_name]
                    with st.expander(f"📚 {group_name}"):
                        st.write(f"**과목:** {group['subject']}")
                        st.write(f"**멤버:** {', '.join(group['members'])}")
                        st.write(f"**설명:** {group['description']}")
                        
                        if group['creator'] == st.session_state.current_user:
                            if st.button(f"삭제 - {group_name}"):
                                del st.session_state.groups[group_name]
                                user['my_groups'].remove(group_name)
                                DataManager.save_data(GROUPS_FILE, st.session_state.groups)
                                DataManager.save_data(USERS_FILE, {'users': st.session_state.users})
                                st.success(f"'{group_name}' 그룹이 삭제되었습니다!")
                                st.rerun()
        else:
            st.info("참여중인 그룹이 없습니다.")
    
    # 학습 계획 탭
    with tab2:
        st.header("📝 학습 계획")
        
        if user.get('my_groups'):
            selected_group = st.selectbox(
                "그룹 선택",
                user['my_groups'],
                key="plan_group"
            )
            
            if selected_group in st.session_state.groups:
                group = st.session_state.groups[selected_group]
                
                # 새 학습 계획 작성
                with st.expander("새 학습 계획 만들기", expanded=True):
                    plan_title = st.text_input("계획 제목")
                    duration = st.selectbox("계획 기간", ["1주", "1개월", "3개월"])
                    goals = st.text_area("학습 목표")
                    
                    if st.button("계획 생성") and plan_title and goals:
                        with st.spinner("AI가 학습 계획을 생성중입니다..."):
                            prompt = f"""
                            다음 조건으로 학습 계획을 작성해주세요:
                            - 과목: {group['subject']}
                            - 제목: {plan_title}
                            - 기간: {duration}
                            - 목표: {goals}
                            """
                            plan_content = get_ai_response(prompt)
                            
                            if 'plans' not in group:
                                group['plans'] = []
                            
                            group['plans'].append({
                                'title': plan_title,
                                'duration': duration,
                                'goals': goals,
                                'content': plan_content,
                                'creator': st.session_state.current_user,
                                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            
                            DataManager.save_data(GROUPS_FILE, st.session_state.groups)
                            st.success("학습 계획이 생성되었습니다!")
                            st.markdown(plan_content)
                
                # 기존 계획 보기
                if group.get('plans'):
                    st.subheader("기존 학습 계획")
                    for plan in reversed(group['plans']):
                        with st.expander(f"📅 {plan['title']} ({plan['duration']})"):
                            st.write(f"작성자: {plan['creator']}")
                            st.write(f"작성일: {plan['created_at']}")
                            st.write("**학습 목표:**")
                            st.write(plan['goals'])
                            st.write("**상세 계획:**")
                            st.markdown(plan['content'])
    
    # 토론 탭
    with tab3:
        st.header("💭 토론")
        
        if user.get('my_groups'):
            selected_group = st.selectbox(
                "그룹 선택",
                user['my_groups'],
                key="discussion_group"
            )
            
            if selected_group in st.session_state.groups:
                group = st.session_state.groups[selected_group]
                
                # 새 토론 주제 생성
                with st.expander("새 토론 주제 만들기", expanded=True):
                    topic_type = st.selectbox(
                        "토론 유형",
                        ["일반 토론", "찬반 토론", "문제 해결 토론"]
                    )
                    
                    if st.button("토론 주제 생성"):
                        with st.spinner("AI가 토론 주제를 생성중입니다..."):
                            prompt = f"""
                            {group['subject']} 과목에 대한 {topic_type} 주제를 생성해주세요.
                            다음 내용을 포함해주세요:
                            1. 토론 주제
                            2. 주요 논점
                            3. 토론 가이드
                            """
                            topics = get_ai_response(prompt)
                            
                            if 'discussions' not in group:
                                group['discussions'] = []
                            
                            group['discussions'].append({
                                'type': topic_type,
                                'content': topics,
                                'creator': st.session_state.current_user,
                                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M"),
                                'comments': []
                            })
                            
                            DataManager.save_data(GROUPS_FILE, st.session_state.groups)
                            st.success("토론 주제가 생성되었습니다!")
                            st.markdown(topics)
                
                # 토론 참여
                if group.get('discussions'):
                    st.subheader("진행중인 토론")
                    for idx, disc in enumerate(reversed(group['discussions'])):
                        with st.expander(f"💬 {disc['type']} ({disc['created_at']})"):
                            st.markdown(disc['content'])
                            
                            # 의견 입력
                            comment = st.text_area("의견 작성", key=f"comment_{idx}")
                            if st.button("의견 등록", key=f"submit_{idx}"):
                                if 'comments' not in disc:
                                    disc['comments'] = []
                                
                                disc['comments'].append({
                                    'user': st.session_state.current_user,
                                    'text': comment,
                                    'time': datetime.now().strftime("%Y-%m-%d %H:%M")
                                })
                                
                                DataManager.save_data(GROUPS_FILE, st.session_state.groups)
                                st.success("의견이 등록되었습니다!")
                                st.rerun()
                            
                            # 기존 의견 표시
                            if disc['comments']:
                                st.markdown("#### 💬 등록된 의견")
                                for com in disc['comments']:
                                    st.markdown(f"""
                                    > **{com['user']}** - {com['time']}  
                                    > {com['text']}
                                    """)
        else:
            st.info("참여중인 그룹이 없습니다.")     
def show_profile_page():
    try:
        user = st.session_state.users[st.session_state.current_user]
        
        st.title("내 프로필")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # 프로필 이미지 표시
            try:
                if user.get('profile_image') and os.path.exists(user['profile_image']):
                    image = Image.open(user['profile_image'])
                    st.image(image, width=200)
                else:
                    st.image("https://via.placeholder.com/200x200?text=No+Image", width=200)
            except Exception as e:
                st.image("https://via.placeholder.com/200x200?text=Error", width=200)
                print(f"이미지 로드 오류: {str(e)}")
            
            # 프로필 이미지 업데이트
            with st.expander("프로필 이미지 변경"):
                uploaded_file = st.file_uploader(
                    "이미지 선택",
                    type=['png', 'jpg', 'jpeg'],
                    key="profile_image_uploader"
                )
                
                if st.button("이미지 업데이트", key="update_image_btn"):
                    if uploaded_file is not None:
                        try:
                            # 이미지 저장 경로 설정
                            save_path = os.path.join(
                                PROFILE_IMAGES_DIR,
                                f"{st.session_state.current_user}.png"
                            )
                            
                            # 이미지 저장
                            image = Image.open(uploaded_file)
                            image.save(save_path)
                            
                            # 프로필 업데이트
                            user['profile_image'] = save_path
                            DataManager.save_data(USERS_FILE, {'users': st.session_state.users})
                            
                            st.success("프로필 이미지가 업데이트되었습니다!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"이미지 업데이트 중 오류가 발생했습니다: {str(e)}")
                    else:
                        st.warning("이미지를 선택해주세요.")
        
        with col2:
            # 프로필 정보 표시
            st.markdown(f"""
            ### {user['nickname']}님의 프로필
            **아이디:** {st.session_state.current_user}  
            **이메일:** {user['email']}  
            **가입일:** {user['created_at']}
            """)
            
            # 프로필 수정
            with st.expander("프로필 수정", expanded=False):
                new_nickname = st.text_input("새 닉네임", user['nickname'])
                new_email = st.text_input("새 이메일", user['email'])
                new_password = st.text_input("새 비밀번호", type="password")
                confirm_password = st.text_input("새 비밀번호 확인", type="password")
                
                if st.button("프로필 업데이트", key="update_profile_btn"):
                    try:
                        # 비밀번호 확인
                        if new_password and new_password != confirm_password:
                            st.error("비밀번호가 일치하지 않습니다.")
                            return
                        
                        # 프로필 업데이트
                        user.update({
                            'nickname': new_nickname,
                            'email': new_email
                        })
                        
                        # 비밀번호 변경
                        if new_password:
                            user['password'] = hash_password(new_password)
                        
                        # 데이터 저장
                        DataManager.save_data(USERS_FILE, {'users': st.session_state.users})
                        st.success("프로필이 업데이트되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"프로필 업데이트 중 오류가 발생했습니다: {str(e)}")
        
        # 학습 통계
        if user.get('study_records'):
            st.header("📊 학습 통계")
            
            # 과목별 학습 횟수
            subjects = {}
            modes = {}
            
            for record in user['study_records']:
                subjects[record['subject']] = subjects.get(record['subject'], 0) + 1
                modes[record['mode']] = modes.get(record['mode'], 0) + 1
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("과목별 학습 횟수")
                st.bar_chart(subjects)
            with col2:
                st.subheader("학습 모드별 횟수")
                st.bar_chart(modes)
            
            # 최근 학습 기록
            st.header("📝 최근 학습 기록")
            for record in reversed(user['study_records'][-5:]):  # 최근 5개만 표시
                with st.expander(f"{record['date']} - {record['subject']} ({record['mode']})"):
                    for key, value in record.items():
                        if key not in ['date', 'subject', 'mode']:
                            st.write(f"**{key}:** {value}")
        
    except Exception as e:
        st.error(f"프로필 페이지 로드 중 오류가 발생했습니다: {str(e)}")
        if st.button("페이지 새로고침"):
            st.rerun()
 # 채팅방 페이지 표시 함수
def show_chat_page():
    st.title("💬 채팅방")
    
    # 채팅방 목록과 채팅 영역을 나누기 위한 컬럼 생성
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("채팅방 목록")
        
        # 새 채팅방 만들기
        with st.expander("+ 새 채팅방", expanded=False):
            chat_name = st.text_input("채팅방 이름")
            chat_members = st.text_input("참여자 (쉼표로 구분)")
            
            if st.button("채팅방 만들기") and chat_name:
                members = [m.strip() for m in chat_members.split(',')] if chat_members else []
                members.append(st.session_state.current_user)  # 생성자 추가
                success, message = ChatManager.create_chat(
                    chat_name,
                    st.session_state.current_user,
                    members
                )
                if success:
                    st.session_state.current_chat = chat_name
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        # 채팅방 목록 표시
        user = st.session_state.users[st.session_state.current_user]
        if user.get('my_chats'):
            for chat_name in user['my_chats']:
                if chat_name in st.session_state.chats:
                    if st.button(f"💬 {chat_name}"):
                        st.session_state.current_chat = chat_name
                        st.rerun()
    
    with col2:
        if 'current_chat' in st.session_state and st.session_state.current_chat:
            chat = st.session_state.chats[st.session_state.current_chat]
            st.subheader(f"💬 {st.session_state.current_chat}")
            
            # 멤버 목록 표시
            st.caption(f"참여자: {', '.join(chat['members'])}")
            
            # 채팅 메시지 표시
            chat_container = st.container()
            
            with chat_container:
                for msg in chat['messages']:
                    message_class = "user-message" if msg['user'] == st.session_state.current_user else "other-message"
                    st.markdown(f"""
                    <div class="chat-message {message_class}">
                        <b>{msg['user']}</b><br>
                        {msg['message']}<br>
                        <small>{msg['time']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            # 메시지 입력
            message = st.text_input("메시지 입력:", key="message_input")
            col1, col2 = st.columns([6, 1])
            with col2:
                if st.button("전송") and message:
                    success, _ = ChatManager.add_message(
                        st.session_state.current_chat,
                        st.session_state.current_user,
                        message
                    )
                    if success:
                        st.rerun()
        else:
            st.info("채팅방을 선택하거나 새로 만들어주세요!")

# 메인 앱 실행
def main():
    try:
        # 세션 상태 복원
        if not st.session_state.get('initialized'):
            session_data = SessionManager.load_session()
            st.session_state.update(session_data)
            st.session_state.initialized = True

        # 메인 UI
        if not st.session_state.logged_in:
            show_auth_page()
        else:
            # 사이드바
            with st.sidebar:
                st.title(f"👋 환영합니다!")
                user = st.session_state.users[st.session_state.current_user]
                if user.get('profile_image'):
                    st.image(user['profile_image'], width=100)
                st.write(f"**{user['nickname']}** 님")
                
                menu = st.radio(
                    "메뉴 선택",
                    ["홈", "프로필", "개인 학습", "스터디 그룹", "채팅방"]
                )
                
                if st.button("로그아웃"):
                    st.session_state.logged_in = False
                    st.session_state.current_user = None
                    if 'current_chat' in st.session_state:
                        del st.session_state.current_chat
                    SessionManager.save_session()
                    st.rerun()
            
            # 메뉴에 따른 페이지 표시
            if menu == "홈":
                st.title("🎓 AI 학습 도우미")
                st.markdown(f"""
                ### 환영합니다, {user['nickname']}님! 👋
                
                ### 🌟 주요 기능
                1. 📚 **개인 학습**
                   - AI 기반 학습 지원
                   - 맞춤형 문제 풀이
                   - 학습 기록 관리
                
                2. 👥 **스터디 그룹**
                   - 그룹 스터디 관리
                   - 실시간 토론
                   - 학습 계획 수립
                
                3. 💬 **채팅방**
                   - 실시간 채팅
                   - 그룹 채팅
                   - 학습 토론
                """)
            elif menu == "프로필":
                show_profile_page()
            elif menu == "개인 학습":
                show_study_page()
            elif menu == "스터디 그룹":
                show_group_page()
            elif menu == "채팅방":
                show_chat_page()

    except Exception as e:
        error_msg = st.session_state.error_handler.log_error(
            "SystemError",
            str(e),
            st.session_state.get('current_user')
        )
        st.error(error_msg)
        if st.button("앱 재시작"):
            st.rerun()

# 앱 시작
if __name__ == "__main__":
    main()  
class ChatManager:
    @staticmethod
    def create_chat(chat_name, creator, members):
        if chat_name in st.session_state.chats:
            return False, "이미 존재하는 채팅방 이름입니다."
        
        # 멤버 목록에 생성자 추가
        members = list(set(members + [creator]))
        
        st.session_state.chats[chat_name] = {
            'creator': creator,
            'members': members,
            'messages': [],
            'active_users': set(),  # 현재 활성 사용자
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'system_messages': [
                {
                    'type': 'create',
                    'user': creator,
                    'time': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'message': f"채팅방이 생성되었습니다."
                }
            ]
        }
        
        # 각 멤버의 채팅방 목록에 추가
        for member in members:
            if member in st.session_state.users:
                if 'my_chats' not in st.session_state.users[member]:
                    st.session_state.users[member]['my_chats'] = []
                st.session_state.users[member]['my_chats'].append(chat_name)
        
        DataManager.save_data(CHATS_FILE, st.session_state.chats)
        DataManager.save_data(USERS_FILE, {'users': st.session_state.users})
        return True, "채팅방이 생성되었습니다!"

    @staticmethod
    def enter_chat(chat_name, user):
        if chat_name not in st.session_state.chats:
            return False, "채팅방을 찾을 수 없습니다."
        
        chat = st.session_state.chats[chat_name]
        if user not in chat['members']:
            return False, "채팅방 멤버가 아닙니다."
        
        # 활성 사용자 목록에 추가
        chat['active_users'] = set(list(chat.get('active_users', set())) + [user])
        
        # 입장 메시지 추가
        chat['system_messages'].append({
            'type': 'enter',
            'user': user,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'message': f"{user}님이 입장하셨습니다."
        })
        
        DataManager.save_data(CHATS_FILE, st.session_state.chats)
        return True, "채팅방에 입장했습니다."

    @staticmethod
    def leave_chat(chat_name, user):
        if chat_name not in st.session_state.chats:
            return False, "채팅방을 찾을 수 없습니다."
        
        chat = st.session_state.chats[chat_name]
        if user not in chat['members']:
            return False, "채팅방 멤버가 아닙니다."
        
        # 활성 사용자 목록에서 제거
        chat['active_users'] = set(u for u in chat.get('active_users', set()) if u != user)
        
        # 퇴장 메시지 추가
        chat['system_messages'].append({
            'type': 'leave',
            'user': user,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'message': f"{user}님이 퇴장하셨습니다."
        })
        
        DataManager.save_data(CHATS_FILE, st.session_state.chats)
        return True, "채팅방에서 퇴장했습니다."

    @staticmethod
    def add_message(chat_name, user, message):
        if chat_name not in st.session_state.chats:
            return False, "채팅방을 찾을 수 없습니다."
        
        chat = st.session_state.chats[chat_name]
        if user not in chat['members']:
            return False, "채팅방 멤버가 아닙니다."
        
        # 메시지 추가
        chat['messages'].append({
            'user': user,
            'message': message,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        DataManager.save_data(CHATS_FILE, st.session_state.chats)
        return True, "메시지가 전송되었습니다."

def show_chat_page():
    st.title("💬 채팅방")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("채팅방 목록")
        
        # 새 채팅방 만들기
        with st.expander("+ 새 채팅방", expanded=False):
            chat_name = st.text_input("채팅방 이름")
            chat_members = st.text_input("참여자 (쉼표로 구분)")
            
            if st.button("채팅방 만들기") and chat_name:
                members = [m.strip() for m in chat_members.split(',')] if chat_members else []
                members.append(st.session_state.current_user)
                success, message = ChatManager.create_chat(
                    chat_name,
                    st.session_state.current_user,
                    members
                )
                if success:
                    st.session_state.current_chat = chat_name
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        # 채팅방 목록 표시
        user = st.session_state.users[st.session_state.current_user]
        if user.get('my_chats'):
            for chat_name in user['my_chats']:
                if chat_name in st.session_state.chats:
                    chat = st.session_state.chats[chat_name]
                    active_count = len(chat.get('active_users', set()))
                    if st.button(f"💬 {chat_name} ({active_count}명 접속중)"):
                        if 'current_chat' in st.session_state:
                            # 이전 채팅방에서 퇴장
                            ChatManager.leave_chat(
                                st.session_state.current_chat,
                                st.session_state.current_user
                            )
                        st.session_state.current_chat = chat_name
                        # 새 채팅방 입장
                        ChatManager.enter_chat(
                            chat_name,
                            st.session_state.current_user
                        )
                        st.rerun()
    
    with col2:
        if 'current_chat' in st.session_state and st.session_state.current_chat:
            chat = st.session_state.chats[st.session_state.current_chat]
            st.subheader(f"💬 {st.session_state.current_chat}")
            
            # 현재 접속자 표시
            active_users = list(chat.get('active_users', set()))
            st.caption(f"접속중인 멤버: {', '.join(active_users)}")
            
            # 메시지 표시 영역
            chat_container = st.container()
            
            with chat_container:
                # 시스템 메시지와 일반 메시지 모두 표시
                all_messages = (
                    [(msg, 'system') for msg in chat['system_messages']] +
                    [(msg, 'user') for msg in chat['messages']]
                )
                # 시간순 정렬
                all_messages.sort(key=lambda x: x[0]['time'])
                
                for msg, msg_type in all_messages:
                    if msg_type == 'system':
                        # 시스템 메시지 스타일
                        st.markdown(f"""
                        <div style="text-align: center; color: gray; font-size: 0.8em; margin: 5px 0;">
                            {msg['message']} - {msg['time']}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # 일반 메시지 스타일
                        message_class = "user-message" if msg['user'] == st.session_state.current_user else "other-message"
                        st.markdown(f"""
                        <div class="chat-message {message_class}">
                            <b>{msg['user']}</b><br>
                            {msg['message']}<br>
                            <small>{msg['time']}</small>
                        </div>
                        """, unsafe_allow_html=True)
            
            # 메시지 입력
            message = st.text_input("메시지 입력:", key="message_input")
            col1, col2 = st.columns([6, 1])
            with col2:
                if st.button("전송") and message:
                    success, _ = ChatManager.add_message(
                        st.session_state.current_chat,
                        st.session_state.current_user,
                        message
                    )
                    if success:
                        st.rerun()
        else:
            st.info("채팅방을 선택하거나 새로 만들어주세요!")    
            
# 사이트 통계 관리 클래스 추가
class SiteStatsManager:
    @staticmethod
    def load_stats():
        stats_file = os.path.join(DATA_DIR, "site_stats.json")
        if not os.path.exists(stats_file):
            default_stats = {
                'total_visitors': 0,
                'registered_users': 0,
                'active_users': set(),
                'daily_visitors': {},
                'last_reset': datetime.now().strftime("%Y-%m-%d")
            }
            DataManager.save_data(stats_file, default_stats)
            return default_stats
        return DataManager.load_data(stats_file, {})

    @staticmethod
    def save_stats(stats):
        stats_file = os.path.join(DATA_DIR, "site_stats.json")
        # set을 list로 변환하여 저장
        stats_to_save = stats.copy()
        stats_to_save['active_users'] = list(stats['active_users'])
        DataManager.save_data(stats_file, stats_to_save)

    @staticmethod
    def update_visitor_count():
        stats = SiteStatsManager.load_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 날짜가 바뀌면 일일 방문자 초기화
        if today != stats.get('last_reset'):
            stats['daily_visitors'] = {}
            stats['last_reset'] = today
        
        stats['total_visitors'] += 1
        if today not in stats['daily_visitors']:
            stats['daily_visitors'][today] = 0
        stats['daily_visitors'][today] += 1
        
        SiteStatsManager.save_stats(stats)
        return stats

    @staticmethod
    def update_user_stats():
        stats = SiteStatsManager.load_stats()
        stats['registered_users'] = len(st.session_state.users)
        stats['active_users'] = set(user for user in st.session_state.users 
                                  if st.session_state.users[user].get('last_active'))
        SiteStatsManager.save_stats(stats)
        return stats

# 사이트 통계 표시 컴포넌트
def show_site_stats():
    stats = SiteStatsManager.load_stats()
    stats['active_users'] = set(stats.get('active_users', []))  # list를 set으로 변환
    
    today = datetime.now().strftime("%Y-%m-%d")
    daily_visitors = stats.get('daily_visitors', {}).get(today, 0)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 사이트 통계")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        st.metric("총 방문자", stats.get('total_visitors', 0))
        st.metric("오늘 방문자", daily_visitors)
    
    with col2:
        st.metric("가입 회원", stats.get('registered_users', 0))
        st.metric("접속 회원", len(stats.get('active_users', set())))

# UserManager 클래스에 사용자 활성 상태 관리 메서드 추가
class UserManager:
    # ... (기존 메서드들은 유지)

    @staticmethod
    def update_user_activity(username):
        if username in st.session_state.users:
            st.session_state.users[username]['last_active'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            DataManager.save_data(USERS_FILE, {'users': st.session_state.users})
            SiteStatsManager.update_user_stats()

    @staticmethod
    def login_user(username, password):
        if username not in st.session_state.users:
            return False, "존재하지 않는 아이디입니다."
        
        user = st.session_state.users[username]
        if user['password'] == hash_password(password):
            st.session_state.logged_in = True
            st.session_state.current_user = username
            UserManager.update_user_activity(username)
            SessionManager.save_session()
            return True, "로그인 성공!"
        return False, "비밀번호가 일치하지 않습니다."

# main 함수에 통계 업데이트 추가
def main():
    try:
        # 방문자 수 업데이트
        SiteStatsManager.update_visitor_count()
        
        # 세션 상태 복원
        if not st.session_state.get('initialized'):
            session_data = SessionManager.load_session()
            st.session_state.update(session_data)
            st.session_state.initialized = True

        # 메인 UI
        if not st.session_state.logged_in:
            # 로그인하지 않은 상태에서도 통계 표시
            show_site_stats()
            show_auth_page()
        else:
            # 사용자 활성 상태 업데이트
            UserManager.update_user_activity(st.session_state.current_user)
            
            # 사이드바
            with st.sidebar:
                st.title(f"👋 환영합니다!")
                user = st.session_state.users[st.session_state.current_user]
                if user.get('profile_image'):
                    st.image(user['profile_image'], width=100)
                st.write(f"**{user['nickname']}** 님")
                
                menu = st.radio(
                    "메뉴 선택",
                    ["홈", "프로필", "개인 학습", "스터디 그룹", "채팅방"]
                )
                
                # 통계 표시
                show_site_stats()
                
                if st.button("로그아웃"):
                    st.session_state.logged_in = False
                    st.session_state.current_user = None
                    if 'current_chat' in st.session_state:
                        del st.session_state.current_chat
                    SessionManager.save_session()
                    st.rerun()
            
            # 메뉴에 따른 페이지 표시
            if menu == "홈":
                st.title("🎓 AI 학습 도우미")
                st.markdown(f"""
                ### 환영합니다, {user['nickname']}님! 👋
                
                ### 🌟 주요 기능
                1. 📚 **개인 학습**
                   - AI 기반 학습 지원
                   - 맞춤형 문제 풀이
                   - 학습 기록 관리
                
                2. 👥 **스터디 그룹**
                   - 그룹 스터디 관리
                   - 실시간 토론
                   - 학습 계획 수립
                
                3. 💬 **채팅방**
                   - 실시간 채팅
                   - 그룹 채팅
                   - 학습 토론
                """)
            # ... (나머지 메뉴 처리 코드는 그대로 유지)

    except Exception as e:
        error_msg = st.session_state.error_handler.log_error(
            "SystemError",
            str(e),
            st.session_state.get('current_user')
        )
        st.error(error_msg)
        if st.button("앱 재시작"):
            st.rerun()            
            
                                                            