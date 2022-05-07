import sys
import os
import sqlite3
import datetime
import time
from PIL import Image

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QDoubleValidator, QPixmap
from PyQt5.QtWidgets import QPushButton, QTableWidgetItem, QMessageBox, QInputDialog, QFileDialog
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QStackedWidget, QLabel

# Импорт модуля из другой папки (Здесь нет ошибки)
sys.path.insert(1, '../MS_Telebot/')
from api_sheets import call_metals_prices
from api_sheets import record, delete_last_row, record_minus_operation


# Загрузка базы данных
con = sqlite3.connect('DataBase/Metals_with_data.db')
cur = con.cursor()

# Загрузка типов металлов с exel
metals_dict = dict(call_metals_prices())
metals_list = call_metals_prices()


# Функция позволяет понять, стоит ли вещественное число, делать целым
def isint(digit):
    if digit[-2:] == '.0':
        return True
    return False


# Окно Главного меню
class MainMenuWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(r'UI\\MainMenuWindow.ui', self)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Запись весов металла')

        # Кнопки
        self.btn_allOperations.clicked.connect(self.all_operations)
        self.btn_actualPrices.clicked.connect(self.actual_price_window)
        self.btn_summaryPage.clicked.connect(self.summary_statistics_window)
        self.btn_completedOperation.clicked.connect(self.completed_operations)

        stacked_widgets.currentChanged.connect(self.add_types_in_scroll_area)
        self.add_types_in_scroll_area()

    # Функия сменяющая окно 'Меню', на окно 'Все операции'
    def all_operations(self):
        all_op = AllOperationsWindow('all_operations')
        stacked_widgets.addWidget(all_op)
        stacked_widgets.setCurrentIndex(stacked_widgets.indexOf(all_op))

    # Функия сменяющая окно 'Меню', на окно 'Актуальные Цены'
    def actual_price_window(self):
        actual_price = ActualPriceWindow()
        stacked_widgets.addWidget(actual_price)
        stacked_widgets.setCurrentIndex(stacked_widgets.indexOf(actual_price))

    # Функия сменяющая окно 'Меню', на окно 'Общие веса металлов'
    def summary_statistics_window(self):
        summary_stats = SummaryStatistics()
        stacked_widgets.addWidget(summary_stats)
        stacked_widgets.setCurrentIndex(stacked_widgets.indexOf(summary_stats))

    # Функия сменяющая окно 'Меню', на окно Добавления веса металла
    def add_weight_metal(self):
        add_weight = AddWeightMetalWindow(self.sender().text())
        stacked_widgets.addWidget(add_weight)
        stacked_widgets.setCurrentIndex(stacked_widgets.indexOf(add_weight))

    # Функия сменяющая окно 'Меню', на окно 'Завершённые операции'
    def completed_operations(self):
        completed_op = CompletedOperationButtonsWindow()
        stacked_widgets.addWidget(completed_op)
        stacked_widgets.setCurrentIndex(stacked_widgets.indexOf(completed_op))

    # Функия заносящяя типы металлов из базы данных в окошко кнопок
    def add_types_in_scroll_area(self):
        # Сначала удаляем все кнопки из scrollArea
        for i in range(self.verticalLayout_2.count()):
            self.verticalLayout_2.itemAt(i).widget().deleteLater()
        # Теперь загружаем кнопки
        # list_metals = cur.execute('SELECT metal FROM metals_prices').fetchall()
        for metal in metals_dict.keys():
            btn = QPushButton(metal, self)
            btn.clicked.connect(self.add_weight_metal)
            self.verticalLayout_2.addWidget(btn)
            btn.setFont(QFont('Arial', 18))


# Окно Добавления веса металла
class AddWeightMetalWindow(QWidget):
    def __init__(self, metal):
        super().__init__()
        uic.loadUi(r'UI\\AddWeightWindow.ui', self)
        self.flag_check_solve = False  # Флаг нужен для проверки выполнилась ли функия solve
        self.metal = metal
        temp_price = metals_dict[metal]
        # temp_price нужен был для того чтобы, проверить стоит ли temp_price превращать в int
        self.price = int(temp_price) if isint(str(temp_price)) else temp_price
        self.initUI()

    def initUI(self):
        # Кнопки
        self.btn_goBack.clicked.connect(self.to_return)
        self.btn_add.clicked.connect(self.add_data)

        # Занесение данных в QLineEdits
        self.lineEdit_date.setText(str(datetime.date.today()).replace('-', '.'))
        self.lineEdit_time.setText(time.strftime("%H:%M", time.localtime()))
        self.lineEdit_metal.setText(self.metal)
        self.lineEdit_quantity.returnPressed.connect(self.solve)
        self.lineEdit_quantity.setValidator(QDoubleValidator())
        self.lineEdit_price.setValidator(QDoubleValidator())
        self.lineEdit_price.setText(str(self.price))
        self.lineEdit_price.returnPressed.connect(self.solve)
        self.checkBox_negative.stateChanged.connect(self.set_negative)

    # Функия возвращения в меню
    def to_return(self):
        stacked_widgets.setCurrentIndex(0)
        stacked_widgets.removeWidget(self)

    # Функция для счёта и выставления данных в QLineEdits
    def solve(self):
        quantity = self.lineEdit_quantity.text().replace(',', '.')
        price = self.lineEdit_price.text()
        if quantity and price:
            try:
                summary = round(float(quantity) * (float(price)), 4)
                self.lineEdit_sum.setText(str(int(summary) if isint(str(summary)) else summary))
                self.flag_check_solve = True
            except ValueError:
                self.flag_check_solve = False
        else:
            self.flag_check_solve = False

    # Функция для добавления данных в базу
    def add_data(self):
        # Проверка на то, выполнена ли функция solve
        if self.flag_check_solve and self.lineEdit_quantity.text():
            date_now = str(datetime.date.today()).replace('-', '.')
            time_now = time.strftime("%H:%M", time.localtime())
            quantity = float(self.lineEdit_quantity.text().replace(',', '.'))
            price = float(self.lineEdit_price.text())
            amount = float(self.lineEdit_sum.text())
            comment = self.plainText_comment.toPlainText()

            # Собираем данные которые будем заносить в базу данных
            values = (date_now, time_now, self.metal, quantity, price, amount, comment)
            # Заносим в общую базу данных на сервере
            record(values)
            # Заносим в базу данных на пк
            cur.execute(f"INSERT INTO all_operations(date, time, metal, quantity,"
                        f" price, sum, comment) "
                        f"VALUES(?, ?, ?, ?, ?, ?, ?);", values)
            # Сбрасываем id Автоинкремент
            cur.execute("UPDATE SQLITE_SEQUENCE SET seq = 0 WHERE name = 'all_operations'")
            con.commit()
            # Сбрасываем таблицы с данные после занесения
            self.lineEdit_quantity.setText('')
            self.lineEdit_price.setText(str(self.price))
            self.lineEdit_sum.setText('')
            self.plainText_comment.setPlainText('')

            self.label_answer.setText('Успешно добавлено!')
            self.label_answer.setStyleSheet('background-color: rgb(85, 255, 127);')
            self.checkBox_negative.setChecked(False)
            self.flag_check_solve = False
        else:
            self.label_answer.setText('Неправильно внесены данные!')
            self.label_answer.setStyleSheet('background-color: rgb(255, 60, 26);')

    # Функия ставящяя минус в начало
    def set_negative(self):
        digits = self.lineEdit_quantity.text()
        if self.checkBox_negative.isChecked() and ('-' not in digits):
            self.lineEdit_quantity.setText(f'-{digits}')
            self.solve()
        elif '-' in digits:
            self.lineEdit_quantity.setText(digits[1:])
            self.solve()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.to_return()


# Окно Всех операций
class AllOperationsWindow(QWidget):
    def __init__(self, name_db):
        super().__init__()
        uic.loadUi(r'UI\\AllOperationsWindow.ui', self)
        self.name_db = name_db
        self.initUI()

    def initUI(self):
        self.btn_goBack.clicked.connect(self.to_return)
        if self.name_db != 'all_operations':
            self.btn_removeOperation.setHidden(True)
        else:
            self.btn_removeOperation.clicked.connect(self.remove_selected_operations)
        # Добавляем названия металлов в comboBox Сортировка по металлу
        for metal in metals_list:
            self.comboBox_metals.addItem(metal[0])
        # Подключаем загрузку таблицы к radioButtons, и сразу же вызываем с 'Все операции'
        self.radiobuttonGroup.buttonClicked.connect(self.load_table)
        self.comboBox_metals.currentIndexChanged.connect(self.load_table)
        self.load_table()

    # Функия возвращения в меню
    def to_return(self):
        if self.name_db == 'all_operations':
            index = 0
        else:
            index = 2
        stacked_widgets.setCurrentIndex(index)
        stacked_widgets.removeWidget(self)

    def load_table(self):
        metal = self.comboBox_metals.currentText()
        metal_filter_rule = '' if metal == 'Все' else f'AND WHERE metal = "{metal}"'
        # Фильтрация данных по radioButton и по comboBox_metals
        if self.radiobuttonGroup.checkedButton().text() == 'Только минусовые':
            data = reversed(cur.execute(f"""SELECT * FROM {self.name_db}
                                            WHERE quantity < 0
                                            {metal_filter_rule[:3]}
                                            {metal_filter_rule[10:]}""").fetchall())
        elif self.radiobuttonGroup.checkedButton().text() == 'Только Плюсовые':
            data = reversed(cur.execute(f"""SELECT * FROM {self.name_db}
                                            WHERE quantity > 0
                                            {metal_filter_rule[:3]}
                                            {metal_filter_rule[10:]}""").fetchall())
        else:
            data = reversed(cur.execute(f"""SELECT * FROM {self.name_db}
                                            {metal_filter_rule[4:]}""").fetchall())
        # Загрузка таблицы
        self.tableWidget.setColumnCount(8)
        self.tableWidget.setHorizontalHeaderLabels(["Дата", "Время", "Тип металла", "Количество",
                                                    "Цена", "Сумма", "Комментарий", "id"])
        self.tableWidget.setRowCount(0)
        for i, row in enumerate(data):
            self.tableWidget.setRowCount(
                self.tableWidget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget.setItem(
                    i, j, QTableWidgetItem(str(elem)))

    # Функия удаляющая строки где выделенне хоть одна ячейка
    def remove_selected_operations(self):
        rows = list(set([i.row() for i in self.tableWidget.selectedItems()]))[::-1]
        data = []
        # Добавляем в data строку, где выделянна ячейка для того чтобы, удалить данные из базы
        for i in rows:
            temp_data = []
            for j in range(self.tableWidget.columnCount()):
                temp_data.append(self.tableWidget.item(i, j).text())
            data.append(temp_data)
        # Сначала удаляем строки
        for index in rows:
            self.tableWidget.model().removeRow(index)
        # Теперь удаляям данные из базы
        for item in data:
            cur.execute(f"""DELETE FROM {self.name_db} 
                            WHERE id = {item[-1]}""")
            con.commit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.remove_selected_operations()
        elif event.key() == Qt.Key_Escape:
            self.to_return()


# Окно Актуальных цен
class ActualPriceWindow(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi(r'UI\\ActualPricesWindow.ui', self)
        self.initUI()
        self.btn_goBack.clicked.connect(self.to_return)

    def initUI(self):
        # Загрузка таблицы
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["Тип металла", "Цена"])
        self.tableWidget.setRowCount(0)
        for i, row in enumerate(metals_list):
            self.tableWidget.setRowCount(
                self.tableWidget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget.setItem(
                    i, j, QTableWidgetItem(str(elem)))

    # Функия возвращения в меню
    def to_return(self):
        stacked_widgets.setCurrentIndex(0)
        stacked_widgets.removeWidget(self)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.to_return()


# Окно Общих весов металла
class SummaryStatistics(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi(r'UI\\SummaryStatisticsWindow.ui', self)
        # Кнопки
        self.btn_goBack.clicked.connect(self.to_return)
        self.btn_resetOperation.clicked.connect(self.reset_to_zero)
        self.comboBox.currentTextChanged.connect(self.load_table)
        self.load_table('Общее')

    # Функия возвращения в меню
    def to_return(self):
        stacked_widgets.setCurrentIndex(0)
        stacked_widgets.removeWidget(self)

    def load_table(self, text):
        metals_with_weights = []
        self.date = str(datetime.date.today()).replace('-', '.')
        metal_date_filter = '' if text == 'За всё время' else f'AND date = "{self.date}"'
        # Собираем данные по определённому запросу
        for metal in metals_list:
            weight = round(sum(map(lambda x: x[0], cur.execute(f"""SELECT quantity
                                                                FROM all_operations
                                                                WHERE metal = '{metal[0]}'
                                                                {metal_date_filter}
                                                                """).fetchall())), 4)
            metals_with_weights.append((metal[0], weight))
        # Загрузка таблицы
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["Тип металла", "Количество"])
        self.tableWidget.setRowCount(0)
        for i, row in enumerate(metals_with_weights):
            self.tableWidget.setRowCount(
                self.tableWidget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget.setItem(
                    i, j, QTableWidgetItem(str(elem)))

    # Функиця обнуляющая выбранный тип металла
    def reset_to_zero(self):
        check = QMessageBox.question(self, 'Обнуление',
                                           f"Вы уверены что хотите обнулить выбранные "
                                           f"типы металлов?"
                                           f" Это перенесёт в архив все операции связанные с ним?",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        # Если человек нажал на yes то сработает функция
        if check == QMessageBox.Yes and self.tableWidget.selectedItems():
            time_now = time.strftime("%H:%M", time.localtime())
            rows = len(list(set([i.row() for i in self.tableWidget.selectedItems()])))
            # Сбрасываем id Автоинкремент
            cur.execute("UPDATE SQLITE_SEQUENCE SET seq = 0 WHERE name = 'buttons_completed_op'")
            # Если человек выделил больше одного столбца то функия не сработает
            if rows > 1:
                return
            else:
                r = self.tableWidget.selectedItems()[0].row()

                # Собираем данные
                weight_from_sys = float(self.tableWidget.item(r, 1).text())
                weight_true = float(QInputDialog.getInt(self, "Вес металла",
                                                        "Введите вес получившийся после отправки",
                                                        min=0)[0])
                metal = self.tableWidget.item(r, 0).text()

                # Берём путь к файлу
                cheque_path = QFileDialog.getOpenFileName(
                    self, 'Выбрать картинку', '',
                    'Картинка (*.jpg);;Картинка (*.png);;Все файлы (*)')[0]
                # Если человек выбрал картинку то, картинка сохраниться в программе
                if cheque_path:
                    path = cheque_path.replace('/', r'\\')
                    count = len(cur.execute('SELECT * FROM buttons_completed_op').fetchall()) + 1
                    im = Image.open(path)
                    im.save(fr"{os.path.abspath('PhotosOfCheques')}\\{str(count)}.jpg")
                    color = '(152, 251, 152)'
                else:
                    color = '(255, 215, 0)'
                values = (self.date, time_now, metal, weight_from_sys, weight_true, color)
                # Добавляем в базу данные для кнопок в окне Завершённые операции
                cur.execute(f"INSERT INTO buttons_completed_op(date, time, metal, weight_from_sys,"
                            f" weight_true, color) VALUES(?, ?, ?, ?, ?, ?);", values)
                self.tableWidget.setItem(r, 1, QTableWidgetItem(str('0')))
                # Переносим данные из Все операции в Архив операций
                cur.execute(f"""INSERT INTO completed_operations
                                                SELECT date, time, metal, quantity, price,
                                                sum, comment FROM all_operations
                                                WHERE metal = '{metal}';""")
                cur.execute(f"DELETE FROM all_operations WHERE metal = '{metal}'")
                con.commit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.to_return()


# Окно Завершённые операции
class CompletedOperationButtonsWindow(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi(r'UI\\CompletedOperationButtonsWindow.ui', self)
        self.btn_goBack.clicked.connect(self.to_return)
        self.btn_archiveOperations.clicked.connect(self.archiveOperations)
        self.add_types_in_scroll_area()

    # Функия возвращения в меню
    def to_return(self):
        stacked_widgets.setCurrentIndex(0)
        stacked_widgets.removeWidget(self)

    # Функия заносящяя типы металлов из базы данных в окошко кнопок
    def add_types_in_scroll_area(self):
        # Теперь загружаем кнопки
        for name_data in reversed(cur.execute('SELECT * FROM buttons_completed_op').fetchall()):
            btn = QPushButton(f'{name_data[0]}.    {"    ".join(name_data[1:4])}', self)
            btn.setStyleSheet(f'background-color: rgb{name_data[-1]};')
            btn.clicked.connect(self.completedOperation)
            self.verticalLayout_2.addWidget(btn)
            btn.setFont(QFont('Arial', 18))

    # Окно Архива операций
    def archiveOperations(self):
        archive_op = AllOperationsWindow('completed_operations')
        stacked_widgets.addWidget(archive_op)
        stacked_widgets.setCurrentIndex(stacked_widgets.indexOf(archive_op))

    # Окно Оконченой операции
    def completedOperation(self):
        archive_op = CompletedOperationWindow(self.sender().text().split('.')[0])
        stacked_widgets.addWidget(archive_op)
        stacked_widgets.setCurrentIndex(stacked_widgets.indexOf(archive_op))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.to_return()


# Окно Оконченной операции
class CompletedOperationWindow(QWidget):
    def __init__(self, n):
        super().__init__()
        uic.loadUi(r'UI\\CompletedOperationWindow.ui', self)
        self.btn_goBack.clicked.connect(self.to_return)
        self.name_photo = n
        self.initUI()

    def initUI(self):
        # Берём данные где номер изображения равен id
        data = cur.execute(f"SELECT * FROM buttons_completed_op "
                           f"WHERE id = {self.name_photo}").fetchone()
        if data[-1] == '(255, 215, 0)':
            self.btn_showCheque.setHidden(True)
        weight_diff = float(data[4]) - float(data[5])
        self.btn_showCheque.clicked.connect(self.show_cheque)

        # Выставляем данные на линиях
        self.label_weightSys.setText(f'{data[4]} кг')
        self.label_weight.setText(f'{data[5]} кг')
        self.label_weightDiff.setText(f'{float(data[4]) - float(data[5])} кг')
        if weight_diff < 0:
            self.label_weightDiff.setText(f'Вы забыли записать: {abs(weight_diff)} кг')
        elif weight_diff > 0:
            self.label_weightDiff.setText(f'Вы записали лишние: {abs(weight_diff)} кг')
        else:
            self.label_weightDiff.setText(weight_diff)

    # Функия возвращения в меню
    def to_return(self):
        stacked_widgets.setCurrentIndex(2)
        stacked_widgets.removeWidget(self)

    # Окно Чека
    def show_cheque(self):
        cheque = ChequeWindow(str(self.name_photo))
        stacked_widgets.addWidget(cheque)
        stacked_widgets.setCurrentIndex(stacked_widgets.indexOf(cheque))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.to_return()


# Окно Чека
class ChequeWindow(QWidget):
    def __init__(self, n):
        super().__init__()
        pic = QPixmap(fr"{os.path.abspath('PhotosOfCheques')}\\{str(n)}.jpg")
        label = QLabel(self)
        label.setPixmap(pic)
        stacked_widgets.setFixedSize(pic.width(), pic.height())
        self.resize(pic.width(), pic.height())

    # Функия возвращения в меню
    def to_return(self):
        stacked_widgets.setFixedSize(1120, 750)
        stacked_widgets.setCurrentIndex(2)
        stacked_widgets.removeWidget(self)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.to_return()


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    stacked_widgets = QStackedWidget()
    # Создаём окна в которых не надо обновлять данные при загрузке
    main_menu_window = MainMenuWindow()
    # Добавляем окна в stacked_widgets
    stacked_widgets.addWidget(main_menu_window)
    stacked_widgets.setFixedSize(1120, 750)
    stacked_widgets.setWindowTitle("Учёт металла")
    stacked_widgets.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())