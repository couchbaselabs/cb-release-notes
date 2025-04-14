pyinstaller cb_release_note.py --onefile --clean --name cb-release-note \
--collect-all pyfiglet \
--collect-all alive_progress \
--collect-all grapheme \
--collect-all openai \
--collect-all numpy \

mkdir ./package
cp ./dist/cb-release-note ./package
cp ./cb_release_notes_config.yaml ./package
cp ./cb_release_config_schema.yaml ./package

# Don't pack the password file.
cp ./passwords_template.yaml ./package/.passwords.yaml

cp -r ./templates ./package
cd package || exit
zip -r  ../package.zip .
cd ..




