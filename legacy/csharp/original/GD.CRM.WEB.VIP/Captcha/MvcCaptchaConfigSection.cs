using System.Configuration;

namespace Dchien.Legal.Web.Captcha
{
    public class CaptchaConfigSection : ConfigurationSection 
    {
        public static CaptchaConfigSection GetConfig()
        {
            return ConfigurationManager.GetSection("captchaGroup/captchaOptions") as CaptchaConfigSection;
        }

        [ConfigurationProperty("textLength",IsRequired = false,DefaultValue = 4)]
        public int TextLength
        {
            get
            {
                int length=(int) this["textLength"];
                return length < 3 ? 3 : length;
            }
        }

        [ConfigurationProperty("textChars", IsRequired = false, DefaultValue = "REDACTED_ARCHIVE_ONLY")]
        public string TextChars
        {
            get
            {
                string chars=(string) this["textChars"];
                return chars.Length < 3 ? "REDACTED_ARCHIVE_ONLY" : chars;
            }
        }

        [ConfigurationProperty("fontWarp", IsRequired = false, DefaultValue = Level.Medium)]
        public Level FontWarp
        {
            get
            {
                return (Level)this["fontWarp"];
            }
        }

        [ConfigurationProperty("lineNoise", IsRequired = false, DefaultValue = Level.Low)]
        public Level LineNoise
        {
            get
            {
                return (Level)this["lineNoise"];
            }
        }

        [ConfigurationProperty("backgroundNoise", IsRequired = false, DefaultValue = Level.Low)]
        public Level BackgroundNoise
        {
            get
            {
                return (Level)this["backgroundNoise"];
            }
        }
    }
}
