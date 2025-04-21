from datetime import datetime, timedelta
import uuid
import hashlib
from db import Database
from models import User, Referral
from config import BOT_TOKEN

class ReferralService:
    def __init__(self):
        self.db = Database()
        self.users_collection = self.db.get_collection('users')
        self.referrals_collection = self.db.get_collection('referrals')
        # Extract bot username from token or use a default
        self.bot_username = self._get_bot_username()
    
    def _get_bot_username(self):
        """
        Use the bot username directly instead of extracting from token
        """
        # استخدام اسم المستخدم الفعلي للبوت بدلاً من معرف البوت
        return "BS_NASHER_bot"  # تم تعيين اسم المستخدم الصحيح للبوت
    
    def generate_referral_link(self, user_id):
        """
        Generate a unique referral link for user
        Returns:
            - referral link string
        """
        # Get user from database
        user = self.users_collection.find_one({'user_id': user_id})
        if not user:
            return None
        
        # Check if user already has a referral code
        if 'referral_code' in user and user['referral_code']:
            referral_code = user['referral_code']
        else:
            # Generate a unique referral code
            referral_code = self._generate_referral_code(user_id)
            
            # Save referral code to user
            self.users_collection.update_one(
                {'user_id': user_id},
                {'$set': {
                    'referral_code': referral_code,
                    'updated_at': datetime.now()
                }}
            )
        
        # Create referral link with bot username
        referral_link = f"https://t.me/{self.bot_username}?start=ref_{referral_code}"
        
        return referral_link
    
    def _generate_referral_code(self, user_id):
        """
        Generate a unique referral code
        Returns:
            - referral code string
        """
        # Create a unique string based on user_id and current time
        unique_str = f"{user_id}_{datetime.now().timestamp()}_{uuid.uuid4()}"
        
        # Hash the string to create a shorter code
        hash_obj = hashlib.md5(unique_str.encode())
        hash_str = hash_obj.hexdigest()
        
        # Take first 8 characters of hash
        referral_code = hash_str[:8]
        
        return referral_code
    
    def get_referral_code_from_start_param(self, start_param):
        """
        Extract referral code from start parameter
        Returns:
            - referral code or None
        """
        if start_param and start_param.startswith('ref_'):
            return start_param[4:]  # Remove 'ref_' prefix
        return None
    
    def get_referrer_by_code(self, referral_code):
        """
        Get referrer user by referral code
        Returns:
            - user_id or None
        """
        user = self.users_collection.find_one({'referral_code': referral_code})
        if user:
            return user['user_id']
        return None
    
    def record_referral(self, referrer_id, referred_id):
        """
        Record a new referral
        Returns:
            - (success, message) tuple
        """
        try:
            # Check if referral already exists
            existing_referral = self.referrals_collection.find_one({
                'referrer_id': referrer_id,
                'referred_id': referred_id
            })
            
            if existing_referral:
                return (False, "هذه الإحالة موجودة بالفعل.")
            
            # Create new referral
            referral = Referral(referrer_id, referred_id)
            
            # Save to database
            self.referrals_collection.insert_one(referral.to_dict())
            
            # Update user's referred_by field
            self.users_collection.update_one(
                {'user_id': referred_id},
                {'$set': {
                    'referred_by': referrer_id,
                    'updated_at': datetime.now()
                }}
            )
            
            return (True, "تم تسجيل الإحالة بنجاح.")
            
        except Exception as e:
            print(f"Error in record_referral: {str(e)}")
            return (False, f"حدث خطأ أثناء تسجيل الإحالة: {str(e)}")
    
    def mark_referral_subscribed(self, referrer_id, referred_id):
        """
        Mark referral as subscribed and give reward
        Returns:
            - (success, message) tuple
        """
        try:
            # Find referral
            referral = self.referrals_collection.find_one({
                'referrer_id': referrer_id,
                'referred_id': referred_id
            })
            
            if not referral:
                return (False, "لم يتم العثور على الإحالة.")
            
            # Check if already marked as subscribed
            if referral.get('is_subscribed', False):
                return (False, "تم تسجيل الاشتراك بالفعل.")
            
            # Mark as subscribed
            self.referrals_collection.update_one(
                {'referrer_id': referrer_id, 'referred_id': referred_id},
                {'$set': {
                    'is_subscribed': True,
                    'updated_at': datetime.now()
                }}
            )
            
            # Give reward if not already given
            if not referral.get('reward_given', False):
                # Add 1 day to referrer's subscription
                referrer = self.users_collection.find_one({'user_id': referrer_id})
                if referrer:
                    # Calculate new subscription end date
                    if referrer.get('subscription_end') and referrer['subscription_end'] > datetime.now():
                        new_end_date = referrer['subscription_end'] + timedelta(days=1)
                    else:
                        new_end_date = datetime.now() + timedelta(days=1)
                    
                    # Update subscription end date
                    self.users_collection.update_one(
                        {'user_id': referrer_id},
                        {'$set': {
                            'subscription_end': new_end_date,
                            'updated_at': datetime.now()
                        }}
                    )
                    
                    # Mark reward as given
                    self.referrals_collection.update_one(
                        {'referrer_id': referrer_id, 'referred_id': referred_id},
                        {'$set': {
                            'reward_given': True,
                            'updated_at': datetime.now()
                        }}
                    )
                    
                    return (True, "تم تسجيل الاشتراك ومنح المكافأة بنجاح.")
                else:
                    return (False, "لم يتم العثور على المستخدم المحيل.")
            
            return (True, "تم تسجيل الاشتراك بنجاح.")
            
        except Exception as e:
            print(f"Error in mark_referral_subscribed: {str(e)}")
            return (False, f"حدث خطأ أثناء تسجيل الاشتراك: {str(e)}")
    
    def get_user_referrals(self, user_id):
        """
        Get all referrals made by user
        Returns:
            - list of referrals
        """
        referrals = self.referrals_collection.find({'referrer_id': user_id})
        return list(referrals)
    
    def get_referral_stats(self, user_id):
        """
        Get referral statistics for user
        Returns:
            - dict with stats
        """
        # Get all referrals
        referrals = self.get_user_referrals(user_id)
        
        # Count total, subscribed, and rewarded referrals
        total_referrals = len(referrals)
        subscribed_referrals = sum(1 for r in referrals if r.get('is_subscribed', False))
        rewarded_referrals = sum(1 for r in referrals if r.get('reward_given', False))
        
        # Calculate total reward days
        total_reward_days = rewarded_referrals
        
        return {
            'total_referrals': total_referrals,
            'subscribed_referrals': subscribed_referrals,
            'rewarded_referrals': rewarded_referrals,
            'total_reward_days': total_reward_days
        }
