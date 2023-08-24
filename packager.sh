pyinstaller cb_release_note.py --onefile --collect-all pyfiglet --collect-all alive_progress --collect-all grapheme
mkdir ./package
cp ./dist/cb_release_note ./package
cp ./cb_release_notes_config.yaml ./package
cp ./cb_release_config_schema.yaml ./package
cp ./.passwords.yaml ./package
cp -r ./templates ./package
cd package || exit
zip -r  ../package.zip .
cd ..




