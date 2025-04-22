from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from subscription_service import SubscriptionService
# تعديل: جعل استيراد AuthService اختيارياً
try:
    from auth_service import AuthService
    HAS_AUTH_SERVICE = True
except ImportError:
    HAS_AUTH_SERVICE = False
from group_service import GroupService
from posting_service import PostingService
try:
    from response_service import ResponseService
    HAS_RESPONSE_SERVICE = True
except ImportError:
    HAS_RESPONSE_SERVICE = False
try:
    from referral_service import ReferralService
    HAS_REFERRAL_SERVICE = True
except ImportError:
    HAS_REFERRAL_SERVICE = False
# استيراد مدير الاشتراك في القناة
from channel_subscription import subscription_manager

class StartHelpHandlers:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.subscription_service = SubscriptionService()
        # تعديل: التحقق من وجود الخدمات قبل استخدامها
        if HAS_AUTH_SERVICE:
            self.auth_service = AuthService()
        else:
            self.auth_service = None
        self.group_service = GroupService()
        self.posting_service = PostingService()
        if HAS_RESPONSE_SERVICE:
            self.response_service = ResponseService()
        else:
            self.response_service = None
        if HAS_REFERRAL_SERVICE:
            self.referral_service = ReferralService()
        else:
            self.referral_service = None

        # Register handlers
        self.register_handlers()

    def register_handlers(self):
        # Register start and help commands
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))

        # Register callback queries - Fix: Use more specific pattern to avoid conflicts
        self.dispatcher.add_handler(CallbackQueryHandler(self.start_help_callback, pattern='^(start_|help_)'))

    # تحديث قائمة الأوامر المرئية للمستخدم بناءً على حالة الاشتراك
    async def update_bot_commands(self, context: CallbackContext, user_id: int):
        """تحديث قائمة الأوامر المرئية للمستخدم بناءً على حالة الاشتراك"""
        try:
            # التحقق من حالة اشتراك المستخدم في القناة
            is_subscribed_to_channel = True
            if subscription_manager.is_mandatory_subscription():
                is_subscribed_to_channel = await subscription_manager.check_user_subscription(user_id, context.bot)
            
            # التحقق من حالة اشتراك المستخدم في البوت
            db_user = self.subscription_service.get_user(user_id)
            is_admin = db_user and db_user.is_admin
            has_subscription = db_user and db_user.has_active_subscription()
            
            # تحديد الأوامر المرئية بناءً على حالة الاشتراك
            commands = []
            
            # المشرفون يرون جميع الأوامر دائماً
            if is_admin:
                commands = [
                    BotCommand("start", "بدء استخدام البوت"),
                    BotCommand("help", "عرض المساعدة"),
                    BotCommand("admin", "لوحة المشرف"),
                    BotCommand("subscription", "إدارة الاشتراكات"),
                    BotCommand("broadcast", "إرسال رسالة للمستخدمين"),
                    BotCommand("stats", "إحصائيات البوت")
                ]
            # المستخدمون المشتركون في القناة والبوت يرون أوامر start و help
            elif is_subscribed_to_channel and has_subscription:
                commands = [
                    BotCommand("start", "بدء استخدام البوت"),
                    BotCommand("help", "عرض المساعدة")
                ]
            # المستخدمون غير المشتركين في القناة أو البوت يرون فقط أمر start
            else:
                commands = [
                    BotCommand("start", "بدء استخدام البوت")
                ]
            
            # تحديث قائمة الأوامر للمستخدم
            await context.bot.set_my_commands(commands, scope=BotCommand.SCOPE_USER, user_id=user_id)
            return True
        except Exception as e:
            print(f"خطأ في تحديث قائمة الأوامر: {str(e)}")
            return False

    async def start_command(self, update: Update, context: CallbackContext):
        """Handle the /start command with interactive buttons"""
        user = update.effective_user
        user_id = user.id

        # تحديث قائمة الأوامر المرئية للمستخدم
        await self.update_bot_commands(context, user_id)

        # Get or create user in database
        db_user = self.subscription_service.get_user(user_id)
        if not db_user:
            db_user = self.subscription_service.create_user(
                user_id,
                user.username,
                user.first_name,
                user.last_name
            )

        # Check if admin
        is_admin = db_user and db_user.is_admin

        # التحقق من حالة اشتراك المستخدم في القناة
        is_subscribed_to_channel = True
        if subscription_manager.is_mandatory_subscription():
            is_subscribed_to_channel = await subscription_manager.check_user_subscription(user_id, context.bot)
            
            # إذا كان الاشتراك إجباري والمستخدم غير مشترك وليس مشرفاً، إظهار رسالة الاشتراك فقط
            if not is_subscribed_to_channel and not is_admin:
                channel = subscription_manager.get_required_channel()
                keyboard = [
                    [InlineKeyboardButton("🔔 الاشتراك في القناة", url=f"https://t.me/{channel[1:]}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"⚠️ يجب عليك الاشتراك في {channel} للاستمرار.\n\n"
                    "اضغط على الزر أدناه للاشتراك في القناة. سيتم التحقق تلقائياً من اشتراكك.",
                    reply_markup=reply_markup
                )
                return

        # Welcome message
        welcome_text = f"👋 مرحباً {user.first_name}!\n\n"

        if is_admin:
            welcome_text += "🔰 أنت مسجل كمشرف في النظام.\n\n"

        welcome_text += "🤖 أنا بوت احترافي للنشر التلقائي في مجموعات تيليجرام.\n\n"

        # Check subscription status
        has_subscription = db_user.has_active_subscription()

        # Create keyboard with options
        keyboard = []

        # Add referral button for all users (new feature)
        keyboard.append([
            InlineKeyboardButton("🔗 الإحالة", callback_data="start_referral")
        ])

        if has_subscription:
            if db_user.subscription_end:
                end_date = db_user.subscription_end.strftime('%Y-%m-%d')
                welcome_text += f"✅ لديك اشتراك نشط حتى: {end_date}\n\n"
            else:
                welcome_text += f"✅ لديك اشتراك نشط غير محدود المدة\n\n"

            # Check if user is logged in
            session_string = None
            if self.auth_service is not None:
                session_string = self.auth_service.get_user_session(user_id)
            if session_string:
                welcome_text += "✅ أنت مسجل الدخول بالفعل ويمكنك استخدام جميع ميزات البوت.\n\n"

                # Add main feature buttons
                keyboard.append([
                    InlineKeyboardButton("👥 المجموعات", callback_data="start_groups"),
                    InlineKeyboardButton("📝 النشر", callback_data="start_post")
                ])

                keyboard.append([
                    InlineKeyboardButton("🤖 الردود التلقائية", callback_data="start_responses")
                ])

                # Add account management buttons
                keyboard.append([
                    InlineKeyboardButton("🔄 تحديث المجموعات", callback_data="start_refresh_groups"),
                    InlineKeyboardButton("📊 حالة النشر", callback_data="start_status")
                ])

                # إضافة زر المساعدة فقط إذا كان المستخدم مشتركاً في القناة
                if is_subscribed_to_channel:
                    keyboard.append([
                        InlineKeyboardButton("📋 المساعدة", callback_data="start_help")
                    ])

                # Add admin button if user is admin
                if is_admin:
                    keyboard.append([
                        InlineKeyboardButton("👨‍💼 لوحة المشرف", callback_data="start_admin")
                    ])
            else:
                welcome_text += "⚠️ أنت لم تقم بتسجيل الدخول بعد.\n\n"

                # Add login buttons
                keyboard.append([
                    InlineKeyboardButton("🔑 تسجيل الدخول", callback_data="start_login"),
                    InlineKeyboardButton("🔐 إنشاء Session", callback_data="start_generate_session")
                ])

                # إضافة زر المساعدة فقط إذا كان المستخدم مشتركاً في القناة
                if is_subscribed_to_channel:
                    keyboard.append([
                        InlineKeyboardButton("📋 المساعدة", callback_data="start_help")
                    ])

                # Add admin button if user is admin
                if is_admin:
                    keyboard.append([
                        InlineKeyboardButton("👨‍💼 لوحة المشرف", callback_data="start_admin")
                    ])
        else:
            welcome_text += "⚠️ ليس لديك اشتراك نشط.\n\n"

            # Create keyboard with subscription option
            keyboard.append([
                InlineKeyboardButton("🔔 طلب اشتراك", callback_data="start_subscription")
            ])

            # إضافة زر المساعدة فقط إذا كان المستخدم مشتركاً في القناة
            if is_subscribed_to_channel:
                keyboard.append([
                    InlineKeyboardButton("📋 المساعدة", callback_data="start_help")
                ])

            # Add admin button if user is admin
            if is_admin:
                keyboard.append([
                    InlineKeyboardButton("👨‍💼 لوحة المشرف", callback_data="start_admin")
                ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text=welcome_text,
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: CallbackContext):
        """Handle the /help command with interactive buttons"""
        user = update.effective_user
        user_id = user.id

        # التحقق من حالة اشتراك المستخدم في القناة
        is_subscribed_to_channel = True
        if subscription_manager.is_mandatory_subscription():
            is_subscribed_to_channel = await subscription_manager.check_user_subscription(user_id, context.bot)
            
            # إذا كان الاشتراك إجباري والمستخدم غير مشترك، إظهار رسالة الاشتراك فقط
            if not is_subscribed_to_channel:
                # Get user from database
                db_user = self.subscription_service.get_user(user_id)
                is_admin = db_user and db_user.is_admin
                
                # المشرفون معفون من التحقق
                if not is_admin:
                    channel = subscription_manager.get_required_channel()
                    keyboard = [
                        [InlineKeyboardButton("🔔 الاشتراك في القناة", url=f"https://t.me/{channel[1:]}")],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"⚠️ يجب عليك الاشتراك في {channel} للاستمرار.\n\n"
                        "اضغط على الزر أدناه للاشتراك في القناة. سيتم التحقق تلقائياً من اشتراكك.",
                        reply_markup=reply_markup
                    )
                    return

        # Get user from database
        db_user = self.subscription_service.get_user(user_id)
        is_admin = db_user and db_user.is_admin
        has_subscription = db_user and db_user.has_active_subscription()

        # التحقق من اشتراك المستخدم في البوت
        if not has_subscription and not is_admin:
            # إذا كان المستخدم غير مشترك في البوت وليس مشرفاً، إعادة توجيهه إلى أمر start
            await self.start_command(update, context)
            return

        help_text = "📋 قائمة الأوامر المتاحة:\n\n"

        # Create keyboard with help categories
        keyboard = [
            [InlineKeyboardButton("🔑 أوامر الحساب", callback_data="help_account")],
            [InlineKeyboardButton("👥 أوامر المجموعات", callback_data="help_groups")],
            [InlineKeyboardButton("📝 أوامر النشر", callback_data="help_posting")],
            [InlineKeyboardButton("🤖 أوامر الردود", callback_data="help_responses")],
            [InlineKeyboardButton("🔗 أوامر الإحالات", callback_data="help_referrals")]
        ]

        # Add admin button if user is admin
        if is_admin:
            keyboard.append([
                InlineKeyboardButton("👨‍💼 أوامر المشرف", callback_data="help_admin")
            ])

        # Add back to start button
        keyboard.append([
            InlineKeyboardButton("🔙 العودة للبداية", callback_data="help_back_to_start")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text=help_text,
            reply_markup=reply_markup
        )

    async def start_help_callback(self, update: Update, context: CallbackContext):
        """Handle start and help related callbacks"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        data = query.data

        # التحقق من حالة اشتراك المستخدم في القناة
        is_subscribed_to_channel = True
        if subscription_manager.is_mandatory_subscription():
            is_subscribed_to_channel = await subscription_manager.check_user_subscription(user_id, context.bot)
            
            # إذا كان الاشتراك إجباري والمستخدم غير مشترك، إظهار رسالة الاشتراك فقط
            if not is_subscribed_to_channel:
                # Get user from database
                db_user = self.subscription_service.get_user(user_id)
                is_admin = db_user and db_user.is_admin
                
                # المشرفون معفون من التحقق
                if not is_admin:
                    channel = subscription_manager.get_required_channel()
                    keyboard = [
                        [InlineKeyboardButton("🔔 الاشتراك في القناة", url=f"https://t.me/{channel[1:]}")],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"⚠️ يجب عليك الاشتراك في {channel} للاستمرار.\n\n"
                        "اضغط على الزر أدناه للاشتراك في القناة. سيتم التحقق تلقائياً من اشتراكك.",
                        reply_markup=reply_markup
                    )
                    return

        # Get user from database
        db_user = self.subscription_service.get_user(user_id)
        is_admin = db_user and db_user.is_admin
        has_subscription = db_user and db_user.has_active_subscription()

        # Handle start callbacks - تحسين: تنفيذ الإجراءات مباشرة بدلاً من طلب استخدام الأوامر
        if data == "start_subscription":
            # تنفيذ إجراء طلب الاشتراك مباشرة
            if hasattr(context.bot, 'subscription_handlers') and hasattr(context.bot.subscription_handlers, 'subscription_command'):
                await context.bot.subscription_handlers.subscription_command(update, context)
            else:
                # إذا لم يكن معالج الاشتراك متاحاً، عرض رسالة بديلة
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="💳 *طلب اشتراك جديد*\n\nيرجى التواصل مع المشرف للحصول على اشتراك جديد.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_login":
            # تنفيذ إجراء تسجيل الدخول مباشرة
            if HAS_AUTH_SERVICE and hasattr(context.bot, 'auth_handlers') and hasattr(context.bot.auth_handlers, 'login_command'):
                await context.bot.auth_handlers.login_command(update, context)
            else:
                # إذا لم يكن معالج تسجيل الدخول متاحاً، بدء محادثة تسجيل الدخول
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="🔑 *تسجيل الدخول*\n\nيرجى إرسال رقم الهاتف بتنسيق دولي (مثال: +966123456789).",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_generate_session":
            # تنفيذ إجراء إنشاء جلسة مباشرة
            if HAS_AUTH_SERVICE and hasattr(context.bot, 'auth_handlers') and hasattr(context.bot.auth_handlers, 'generate_session_command'):
                await context.bot.auth_handlers.generate_session_command(update, context)
            else:
                # إذا لم يكن معالج إنشاء الجلسة متاحاً، بدء محادثة إنشاء الجلسة
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="🔐 *إنشاء Session String*\n\nيرجى إرسال API ID الخاص بك.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_groups":
            # تنفيذ إجراء إدارة المجموعات مباشرة
            if hasattr(context.bot, 'group_handlers') and hasattr(context.bot.group_handlers, 'groups_command'):
                await context.bot.group_handlers.groups_command(update, context)
            else:
                # إذا لم يكن معالج المجموعات متاحاً، عرض قائمة المجموعات
                user_id = update.effective_user.id
                groups = self.group_service.get_user_groups(user_id)

                if not groups:
                    keyboard = [[InlineKeyboardButton("🔄 تحديث المجموعات", callback_data="start_refresh_groups")],
                               [InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        text="👥 *المجموعات*\n\nلم يتم العثور على مجموعات. يرجى تحديث المجموعات أولاً.",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                else:
                    # إنشاء لوحة مفاتيح مع المجموعات
                    keyboard = []
                    for group in groups:
                        group_id = str(group.get('group_id'))
                        group_name = group.get('title', 'مجموعة بدون اسم')
                        is_blacklisted = group.get('blacklisted', False)
                        emoji = "🔴" if is_blacklisted else "🟢"
                        keyboard.append([InlineKeyboardButton(f"{emoji} {group_name}", callback_data=f"group:{group_id}")])

                    keyboard.append([InlineKeyboardButton("🔄 تحديث المجموعات", callback_data="start_refresh_groups")])
                    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="start_back")])

                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        text="👥 *المجموعات*\n\nاختر مجموعة للتحكم بها:",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )

        elif data == "start_post":
            # تنفيذ إجراء النشر مباشرة
            if hasattr(context.bot, 'posting_handlers') and hasattr(context.bot.posting_handlers, 'start_post'):
                # استخدام معالج النشر مباشرة
                # نحتاج إلى إنشاء رسالة وهمية لتمرير إلى معالج النشر
                class DummyMessage:
                    def __init__(self, chat_id, from_user):
                        self.chat_id = chat_id
                        self.from_user = from_user

                    async def reply_text(self, text, reply_markup=None, parse_mode=None):
                        # استبدال رسالة الاستعلام بدلاً من إرسال رسالة جديدة
                        await query.edit_message_text(
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode
                        )

                # إنشاء رسالة وهمية
                update.message = DummyMessage(
                    chat_id=update.effective_chat.id,
                    from_user=update.effective_user
                )

                # استدعاء معالج النشر
                await context.bot.posting_handlers.start_post(update, context)
            else:
                # إذا لم يكن معالج النشر متاحاً، عرض رسالة بديلة
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="📝 *النشر في المجموعات*\n\nيرجى استخدام الأمر /post لبدء النشر في المجموعات.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_responses":
            # تنفيذ إجراء الردود التلقائية مباشرة
            if HAS_RESPONSE_SERVICE and hasattr(context.bot, 'response_handlers') and hasattr(context.bot.response_handlers, 'auto_response_command'):
                await context.bot.response_handlers.auto_response_command(update, context)
            else:
                # إذا لم يكن معالج الردود التلقائية متاحاً، عرض رسالة بديلة
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="🤖 *الردود التلقائية*\n\nيمكنك إعداد ردود تلقائية للرسائل الواردة.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_referral":
            # تنفيذ إجراء الإحالة مباشرة
            if HAS_REFERRAL_SERVICE and hasattr(context.bot, 'referral_handlers') and hasattr(context.bot.referral_handlers, 'referral_command'):
                await context.bot.referral_handlers.referral_command(update, context)
            else:
                # إذا لم يكن معالج الإحالة متاحاً، عرض رسالة بديلة
                user_id = update.effective_user.id
                bot_username = (await context.bot.get_me()).username
                referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
                
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=f"🔗 *رابط الإحالة الخاص بك*\n\n"
                         f"`{referral_link}`\n\n"
                         f"شارك هذا الرابط مع أصدقائك للحصول على مكافآت!",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_refresh_groups":
            # تنفيذ إجراء تحديث المجموعات مباشرة
            if hasattr(context.bot, 'group_handlers') and hasattr(context.bot.group_handlers, 'refresh_groups_command'):
                await context.bot.group_handlers.refresh_groups_command(update, context)
            else:
                # إذا لم يكن معالج تحديث المجموعات متاحاً، عرض رسالة بديلة
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="🔄 *تحديث المجموعات*\n\nجاري تحديث قائمة المجموعات...",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_status":
            # تنفيذ إجراء عرض حالة النشر مباشرة
            if hasattr(context.bot, 'posting_handlers') and hasattr(context.bot.posting_handlers, 'status_command'):
                await context.bot.posting_handlers.status_command(update, context)
            else:
                # إذا لم يكن معالج حالة النشر متاحاً، عرض رسالة بديلة
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="📊 *حالة النشر*\n\nلا توجد مهام نشر نشطة حالياً.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_help":
            # تنفيذ إجراء عرض المساعدة مباشرة
            help_text = "📋 قائمة الأوامر المتاحة:\n\n"

            # Create keyboard with help categories
            keyboard = [
                [InlineKeyboardButton("🔑 أوامر الحساب", callback_data="help_account")],
                [InlineKeyboardButton("👥 أوامر المجموعات", callback_data="help_groups")],
                [InlineKeyboardButton("📝 أوامر النشر", callback_data="help_posting")],
                [InlineKeyboardButton("🤖 أوامر الردود", callback_data="help_responses")],
                [InlineKeyboardButton("🔗 أوامر الإحالات", callback_data="help_referrals")]
            ]

            # Add admin button if user is admin
            if is_admin:
                keyboard.append([
                    InlineKeyboardButton("👨‍💼 أوامر المشرف", callback_data="help_admin")
                ])

            # Add back to start button
            keyboard.append([
                InlineKeyboardButton("🔙 العودة للبداية", callback_data="help_back_to_start")
            ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=help_text,
                reply_markup=reply_markup
            )

        elif data == "start_admin":
            # تنفيذ إجراء عرض لوحة المشرف مباشرة
            if hasattr(context.bot, 'admin_handlers') and hasattr(context.bot.admin_handlers, 'admin_command'):
                await context.bot.admin_handlers.admin_command(update, context)
            else:
                # إذا لم يكن معالج لوحة المشرف متاحاً، عرض رسالة بديلة
                keyboard = [
                    [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
                    [InlineKeyboardButton("💳 إدارة الاشتراكات", callback_data="admin_subscriptions")],
                    [InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats")],
                    [InlineKeyboardButton("📢 إرسال رسالة للمستخدمين", callback_data="admin_broadcast")],
                    [InlineKeyboardButton("🔔 إعدادات الاشتراك الإجباري", callback_data="admin_channel_subscription")],
                    [InlineKeyboardButton("🔙 العودة", callback_data="start_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="👨‍💼 *لوحة المشرف*\n\nاختر إحدى الخيارات التالية:",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_back":
            # العودة إلى رسالة البداية
            await self.start_command(update, context)

        # Handle help callbacks
        elif data.startswith("help_"):
            if data == "help_account":
                text = "🔑 *أوامر الحساب*\n\n"
                text += "/start - بدء استخدام البوت\n"
                text += "/help - عرض المساعدة\n"
                text += "/login - تسجيل الدخول\n"
                text += "/logout - تسجيل الخروج\n"
                text += "/session - إنشاء Session String\n"
                text += "/subscription - عرض حالة الاشتراك\n"

                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_help")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

            elif data == "help_groups":
                text = "👥 *أوامر المجموعات*\n\n"
                text += "/groups - عرض قائمة المجموعات\n"
                text += "/refresh - تحديث قائمة المجموعات\n"
                text += "/blacklist - إضافة مجموعة إلى القائمة السوداء\n"
                text += "/whitelist - إزالة مجموعة من القائمة السوداء\n"

                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_help")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

            elif data == "help_posting":
                text = "📝 *أوامر النشر*\n\n"
                text += "/post - بدء النشر في المجموعات\n"
                text += "/status - عرض حالة النشر\n"
                text += "/cancel - إلغاء النشر الحالي\n"
                text += "/schedule - جدولة النشر\n"

                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_help")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

            elif data == "help_responses":
                text = "🤖 *أوامر الردود التلقائية*\n\n"
                text += "/responses - إدارة الردود التلقائية\n"
                text += "/addresponse - إضافة رد تلقائي جديد\n"
                text += "/delresponse - حذف رد تلقائي\n"

                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_help")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

            elif data == "help_referrals":
                text = "🔗 *أوامر الإحالات*\n\n"
                text += "/referral - عرض رابط الإحالة الخاص بك\n"
                text += "/referrals - عرض قائمة الإحالات الخاصة بك\n"

                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_help")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

            elif data == "help_admin":
                text = "👨‍💼 *أوامر المشرف*\n\n"
                text += "/admin - الوصول إلى لوحة المشرف\n"
                text += "/users - إدارة المستخدمين\n"
                text += "/addadmin - إضافة مشرف جديد\n"
                text += "/deladmin - إزالة مشرف\n"
                text += "/addsub - إضافة اشتراك لمستخدم\n"
                text += "/delsub - إزالة اشتراك من مستخدم\n"
                text += "/broadcast - إرسال رسالة للمستخدمين\n"
                text += "/stats - عرض إحصائيات البوت\n"
                text += "/channel - إعدادات الاشتراك الإجباري في القناة\n"

                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_help")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

            elif data == "help_back_to_start":
                # العودة إلى رسالة البداية
                await self.start_command(update, context)
